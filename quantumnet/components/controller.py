import networkx as nx
from ..components import Network, Host, Logger
from qiskit import QuantumCircuit
import random
from collections import defaultdict

class Controller():
    def __init__(self, network):
        """
        Inicializa o controlador com uma instância da rede.
        """
        self.network = network
        self.logger = Logger.get_instance()  
        self.pending_requests = []  
        self.scheduled_requests = {}  # Requisições por timeslot
        self.executed_requests = []  # Histórico de requisições executadas
        self.occupied_routes = {}  # Rastreia rotas ocupadas por timeslot
        self.scheduled_requests_slice = defaultdict(list)
        self.slices = {}

    def initialize_slices(self, network, clients, server, protocols, slice_1_paths, slice_2_paths):
        """
        Inicializa os slices, suas rotas associadas e vincula cada slice a um protocolo.

        Args:
            network (Network): Instância da rede configurada.
            clients (list): Lista de IDs dos clientes.
            server (int): ID do servidor.
            protocols (list): Lista de protocolos para configurar os slices.
            slice_1_paths (list): Rotas calculadas para o slice 1.
            slice_2_paths (list): Rotas calculadas para o slice 2.
        """
        # Passando as rotas diretamente para os atributos
        self.final_slice_1_paths = [slice_1_paths[0]]  
        self.final_slice_2_paths = [slice_2_paths[0]] 

        # Inicializa os slices
        for i, protocol in enumerate(protocols, start=1):
            slice_id = f'slice_{i}'

            # Atribui as rotas aos slices com base nos protocolos
            if i == 1:  # Protocolo 1
                self.slices[slice_id] = {
                    "client": self.final_slice_1_paths[0], 
                }
            elif i == 2:  # Protocolo 2
                self.slices[slice_id] = {
                    "client": self.final_slice_2_paths[0],  
                }
            else:
                raise ValueError("Somente dois slices são suportados atualmente.")
            
            # Inicializa a lista de requisições do protocolo
            self.scheduled_requests_slice[protocol] = []
            
            # Registra as rotas e protocolos nos logs
            self.logger.log(f"Slice {slice_id} configurado para protocolo {protocol} com rotas: {self.slices[slice_id]}")


    def create_routing_table(self, host_id: int) -> dict:
        """
        Cria uma tabela de roteamento com os caminhos mais curtos para cada nó.

        Args:
            host_id (int): ID do host para o qual criar a tabela de roteamento.

        Returns:
            dict: Dicionário de destinos para caminhos mais curtos.
        """
        shortest_paths = nx.shortest_path(self.network.graph, source=host_id)
        routing_table = {dest: path for dest, path in shortest_paths.items()}
        return routing_table
    

    def register_routing_tables(self):
        """
        Registra tabelas de roteamento para todos os nós.
        """
        for host_id in self.network.hosts:
            routing_table = self.create_routing_table(host_id)
            self.network.hosts[host_id].set_routing_table(routing_table)

    # Gerenciamento de Requisições

    def receive_request(self, request):
        """
        Recebe uma requisição e tenta agendá-la.

        Args:
            request (dict): Dicionário com a requisição contendo informações como Alice, Bob, protocolo, etc.
        """
        self.pending_requests.append(request)
        self.logger.log(f"Requisição recebida: {request}")
        self.process_requests()
        
    def process_requests(self, max_attempts=1):
        self.prioritize_requests()
        attempts = 0
        # Suponha que você queira começar no timeslot 1
        # Assim, se o timeslot atual for 0, incrementamos manualmente
        while self.pending_requests and attempts < max_attempts:
            current_timeslot = self.network.get_timeslot()

            # Se quisermos sempre começar do timeslot 1 em diante, podemos fazer:
            if current_timeslot == 0:
                # Avança um timeslot para começar do 1
                self.network.timeslot()
                current_timeslot = self.network.get_timeslot()

            request = self.pending_requests[0]
            if self.try_schedule_request(request, current_timeslot):
                self.pending_requests.pop(0)
                attempts = 0
            else:
                self.logger.log(f"Requisição {request} não pôde ser agendada. Avançando timeslot.")
                self.network.timeslot()
                attempts += 1


    def try_schedule_request(self, request, current_timeslot):
        """
        Tenta agendar uma requisição em um timeslot disponível ou compartilhar um existente.

        Args:
            request (dict): Requisição a ser agendada.
            current_timeslot (int): Timeslot atual.

        Returns:
            bool: True se a requisição foi agendada, False caso contrário.
        """
        alice_id = request['alice_id']
        bob_id = request['bob_id']
        route = self.network.networklayer.short_route_valid(alice_id, bob_id,increment_timeslot=False)

        if route:
            # Tentar reutilizar um timeslot existente
            if current_timeslot in self.scheduled_requests:
                if self.share_timeslot(route, current_timeslot):
                    self.reserve_route(route, current_timeslot)
                    self.scheduled_requests.setdefault(current_timeslot, []).append(request)
                    self.logger.log(f"Requisição agendada no mesmo timeslot {current_timeslot} para rota {route}.")
                    return True

            # Se não for possível reutilizar, busque o próximo disponível
            next_timeslot = self.find_next_available_timeslot(route)
            if self.is_route_available(route, next_timeslot):
                self.reserve_route(route, next_timeslot)
                self.scheduled_requests.setdefault(next_timeslot, []).append(request)
                self.logger.log(f"Requisição agendada: {request} no timeslot {next_timeslot}.")
                return True

        return False


    def share_timeslot(self, route, timeslot):
        """
        Verifica se a nova rota pode compartilhar o timeslot especificado,
        considerando apenas a última requisição na mesma rota.

        Args:
            route (list): A nova rota a ser analisada.
            timeslot (int): O timeslot existente.

        Returns:
            bool: True se a rota pode compartilhar o timeslot, False caso contrário.
        """
        # Obter as requisições do timeslot especificado
        if timeslot not in self.scheduled_requests:
            return True  # Nenhuma requisição, então pode compartilhar

        # Obter a última requisição da rota no mesmo timeslot
        for request in reversed(self.scheduled_requests[timeslot]):
            existing_route = self.network.networklayer.short_route_valid(
                request['alice_id'], request['bob_id']
            )
            # Verificar sobreposição de nós intermediários
            overlapping_nodes = set(route[:-1]).intersection(existing_route[:-1])
            if overlapping_nodes:
                return False  # Conflito encontrado
        return True

    def execute_scheduled_requests(self, timeslot):
        """
        Executa requisições agendadas no timeslot especificado.
        """
        if timeslot not in self.scheduled_requests:
            self.logger.log(f"Nenhuma requisição agendada no timeslot {timeslot}.")
            return

        self.logger.log(f"Executando requisições do timeslot {timeslot}.")
        for request in self.scheduled_requests[timeslot]:
            if self.execute_request_one(request):
                self.executed_requests.append({"request": request, "timeslot": timeslot})

        del self.scheduled_requests[timeslot]  # Limpa as requisições já executadas

    def execute_request_one(self, request):
        """
        Executa uma requisição específica, validando a rota.

        Args:
            request (dict): Requisição a ser executada.

        Returns:
            bool: True se a execução foi bem-sucedida, False caso contrário.
        """
        alice_id = request['alice_id']
        bob_id = request['bob_id']
        route = self.network.networklayer.short_route_valid(alice_id, bob_id)

        if route:
            self.network.execute_request(request)
            self.logger.log(f"Requisição executada: {request}")
            self.release_route(route)
            return True
        self.logger.log(f"Falha ao executar requisição: {request}")
        return False

    # Gerenciamento das Rotas
   
    def is_route_available(self, route, timeslot):
        """
        Verifica se uma rota está livre para uso no timeslot especificado.
        """
        for i in range(len(route) - 1):
            link = (route[i], route[i + 1])
            if self.occupied_routes.get(link) == timeslot:
                self.logger.log(f"Conflito: Link {link} ocupado no timeslot {timeslot}.")
                return False
        return True

    def reserve_route(self, route, timeslot):
        """
        Reserva uma rota para uso no timeslot especificado.

        Args:
            route (list): Rota a ser reservada.
            timeslot (int): Timeslot em que a rota será reservada.
        """
        for i in range(len(route) - 1):
            link = (route[i], route[i + 1])
            self.occupied_routes[link] = timeslot
        self.logger.log(f"Rota reservada: {route} no timeslot {timeslot}.")

    def release_route(self, route):
        """
        Libera a rota, permitindo seu reuso em outros timeslots.

        Args:
            route (list): Rota a ser liberada.
        """
        for i in range(len(route) - 1):
            link = (route[i], route[i + 1])
            self.occupied_routes.pop(link, None)
        self.logger.log(f"Rota liberada: {route}.")

    # Funções Auxiliares 

    def find_next_available_timeslot(self, route):
        """
        Encontra o próximo timeslot em que a rota estará completamente livre.

        Args:
            route (list): Rota a ser verificada.

        Returns:
            int: Próximo timeslot livre para a rota.
        """
        current_timeslot = self.network.get_timeslot()
        while not self.is_route_available(route, current_timeslot):
            current_timeslot += 1
        return current_timeslot

    def prioritize_requests(self):
        """
        Ordena as requisições pendentes com base em critérios de prioridade.
        """
        # Verifica se quantum_circuit é um objeto válido
        self.pending_requests.sort(key=lambda req: (req['num_qubits'], -len(req['quantum_circuit'][0].data)))

    def generate_schedule_report(self):
        """
        Gera um relatório das requisições processadas e agendadas.
        """
        if not self.executed_requests and not self.scheduled_requests:
            print("Nenhuma requisição foi processada ou agendada.")
            return

        print("=== Relatório de Requisições ===")
        if self.executed_requests:
            print("Requisições Executadas:")
            for entry in self.executed_requests:
                req = entry["request"]
                ts = entry["timeslot"]
                print(f"- {req} | Timeslot: {ts}")

        if self.scheduled_requests:
            print("\nRequisições Agendadas:")
            for ts, requests in self.scheduled_requests.items():
                print(f"Timeslot {ts}:")
                for req in requests:
                    print(f"- {req}")

    def send_scheduled_requests(self):
        """
        Executa todas as requisições agendadas em sequência,
        reiniciando a rede após cada timeslot para evitar decoerência.
        """
        self.logger.log("Iniciando execução das requisições agendadas.")
        for ts in sorted(self.scheduled_requests.keys()):
            self.logger.log(f"Processando timeslot {ts}.")
            
            # Executa as requisições do timeslot
            self.execute_scheduled_requests(ts)

            # Após a execução, reinicia a rede
            self.logger.log(f"Estado da rede antes da reinicialização: Timeslot {self.network.get_timeslot()}.")
            self.network.restart_network()
            self.logger.log(f"Rede reiniciada. Timeslot reiniciado para {self.network.get_timeslot()}.")


    # SIMULAÇÃO EM SLICES
    
    def schedule_requests(self, requests, slice_paths=None):
        """
        Mapeia as requisições para slices e agenda-as em timeslots.

        Args:
            requests (list): Lista de requisições.
            slice_paths (dict, optional): Dicionário com os caminhos dos slices. Se não fornecido, será considerado None.

        Returns:
            dict: Timeslots com requisições agendadas.
        """
        scheduled_timeslots = {}
        current_timeslot = 1

        # Mapeia as requisições para os slices corretos
        for request in requests:
            protocol = request.get('protocol')
            for slice_id, slice_protocol in self.scheduled_requests_slice.items():
                if protocol == slice_id:
                    self.scheduled_requests_slice[protocol].append(request)

        # Alterna entre slices para agendar
        while any(self.scheduled_requests_slice.values()):
            current_slot_requests = []

            for protocol, requests in self.scheduled_requests_slice.items():
                if requests:
                    current_slot_requests.append(requests.pop(0))

            if current_slot_requests:
                scheduled_timeslots[current_timeslot] = current_slot_requests
                current_timeslot += 1

        # Verificar se slice_paths não é None antes de tentar acessar
        if slice_paths:
            for timeslot, requests in scheduled_timeslots.items():
                for request in requests:
                    protocol = request.get('protocol')
                    slice_key = 'slice_1' if protocol == 'BFK_BQC' else 'slice_2'
                    path = slice_paths.get(slice_key)  # Tenta acessar a rota associada ao slice
                    if path:
                        request['slice_path'] = path
                    else:
                        self.logger.log(f"Warning: Nenhum caminho encontrado para o slice '{slice_key}'.")

        self.logger.log(f"Requisições agendadas em timeslots: {scheduled_timeslots}")
        return scheduled_timeslots
    

    def map_requests_to_slices(self, requests):
        """
        Mapeia as requisições para slices com base no protocolo.

        Args:
            requests (list): Lista de requisições.

        Returns:
            dict: Requisições separadas por slices.
        """
        slice_requests = {}

        # Mapeamento direto dos protocolos para slices
        protocol_to_slice = {
            'BFK_BQC': 'slice_1',  # Protocolo BFK_BQC para slice 1
            'AC_BQC': 'slice_2',   # Protocolo AC_BQC para slice 2
        }

        for request in requests:
            protocol = request.get('protocol')
            
            # Atribui o slice correto com base no protocolo
            slice_id = protocol_to_slice.get(protocol)
            if slice_id is None:
                raise ValueError(f"Protocolo {protocol} não encontrado para mapeamento de slice.")
            
            if slice_id not in slice_requests:
                slice_requests[slice_id] = []
            slice_requests[slice_id].append(request)

        return slice_requests
    

    def schedule_requests_in_timeslots(self, slice_requests):
        """
        Agenda as requisições em timeslots alternando entre os slices.

        Args:
            slice_requests (dict): Requisições separadas por slices.

        Returns:
            dict: Dicionário de timeslots com requisições agendadas.
        """
        scheduled_timeslots = {}
        current_timeslot = 1

        while any(slice_requests.values()):
            current_slot_requests = []

            # Alterna entre slices para agendar as requisições
            for slice_id, requests in slice_requests.items():
                if requests:
                    current_slot_requests.append(requests.pop(0))

            if current_slot_requests:
                scheduled_timeslots[current_timeslot] = current_slot_requests
                current_timeslot += 1

        return scheduled_timeslots
    
    def print_report(self, scheduled_timeslots, slice_paths):
        """
        Imprime um relatório detalhado de agendamento e execução das requisições no console.

        Args:
            scheduled_timeslots (dict): Dicionário de timeslots com as requisições agendadas.
            slice_paths (dict): Dicionário contendo os caminhos para cada slice.
        """
        print("\n=== Relatório de Agendamento e Execução de Requisições ===\n")
        for timeslot, requests in scheduled_timeslots.items():
            print(f"Timeslot {timeslot}:")
            for request in requests:
                protocol = request['protocol']
                slice_key = 'slice_1' if protocol == 'BFK_BQC' else 'slice_2'
                path = slice_paths.get(slice_key)
                print(f"  - Alice ID: {request['alice_id']}, Bob ID: {request['bob_id']}, "
                    f"Protocolo: {protocol}, Nº de Qubits: {request['num_qubits']}, Caminho do {slice_key}: {path}")
            print("-" * 60)
        print("\n=== Fim do Relatório ===\n")
