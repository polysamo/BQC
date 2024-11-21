import networkx as nx
from ..components import Network, Host, Logger
from qiskit import QuantumCircuit
import random
#get profundidade (depht) do circuito
#numero de timeslots passadod= deplth
class Controller():
    def __init__(self,network):
        """
        Inicializa o controlador com uma instância da rede.
        
        Args:
            network (Network): Instância da rede que o controlador irá gerenciar.
        """
        self.network = network
        self.hosts = None
        self.links = None
        self.logger = Logger.get_instance()  # Obtém uma instância do logger para registrar eventos
        self.pending_requests = []  # Lista para armazenar as requisições recebidas
        self.scheduled_requests = {}  # Dicionário para armazenar requisições por timeslot
        self.occupied_routes = {}  # Rotas ocupadas {route: timeslot}

    def create_routing_table(self, host_id: int) -> dict:
        """
        Create a routing table for a node in a graph.
        Args:
            host_id (int): The node ID to create the routing table for.
        Returns:
            dict: A routing table for the node.
        """
        shortest_paths = nx.shortest_path(self.network.graph, source=host_id)  # Get shortest paths from the node to all other nodes
        routing_table = {}

        for destination, path in shortest_paths.items():
            if len(path) > 1:  # Ensure there's a valid path
                routing_table[destination] = path  # Store the next hop on the shortest path
            else:
                routing_table[destination] = [host_id]  # Self-routing

        return routing_table

    def register_routing_tables(self):
        """
        Register routing tables for all hosts in the network.
        """
        self.hosts = self.network.hosts

        for host_id in self.hosts:
            routing_table = self.create_routing_table(host_id)
            self.hosts[host_id].set_routing_table(routing_table)

    def check_route(self, route):
        """
        Check if a route is valid.
        Args:
            route (list): A list of nodes in the route.
        Returns:
            bool: True if the route is valid, False otherwise.
        """       
        return True

    def announce_to_route_nodes(self, route):
        """
        Announce a message to all nodes in a route.
        Args:
            route (list): A list of nodes in the route.
        """

        if len(route) == 1:
            print(f'Nó {route[0]} informado.')
        for node in route[1:]:
            print(f'Nó {node} informado.')

    def announce_to_alice_and_bob(self, route):
        """
        Announce a message to Alice and Bob.
        Args:
            route (list): A list of nodes in the route.
        """

        print(f"Alice {route[0]} e Bob {route[-1]} informados.")

    def receive_request(self, request):
        """
        Recebe uma nova requisição e adiciona à lista de requisições pendentes.
        """
        self.pending_requests.append(request)
        self.logger.log(f"Requisição recebida: {request}")
        self.process_requests()  # Processa as requisições imediatamente


    def process_requests(self):
        """
        Processa requisições pendentes, alocando imediatamente se recursos estiverem disponíveis,
        e libera os recursos após a execução.
        """
        while self.pending_requests:
            # Tentar alocar a primeira requisição na lista de pendentes
            request = self.pending_requests[0]
            alice_id = request['alice_id']
            bob_id = request['bob_id']
            route = self.network.networklayer.short_route_valid(alice_id, bob_id)

            if route and self.is_route_available(route):
                # Reserva a rota e executa imediatamente
                timeslot = self.network.get_timeslot()
                self.reserve_route(route, timeslot)
                self.logger.log(f"Executando requisição imediata: Alice {alice_id} -> Bob {bob_id}")
                
                self.network.execute_request(request)
                self.release_route(route)  # Libera a rota após execução
                self.pending_requests.pop(0)  # Remove a requisição executada
            else:
                # Se não puder alocar, avança o timeslot
                self.network.timeslot()
                self.logger.log(f"Timeslot avançado para {self.network.get_timeslot()} devido à indisponibilidade de recursos.")

    def schedule_requests(self, requests, max_attempts=10):
        """
        Agenda as requisições recebidas, maximizando o número de requisições processadas em um único timeslot,
        utilizando o timeslot diretamente da rede.
        """
        attempts = 0

        while requests and attempts < max_attempts:
            current_timeslot = self.network.get_timeslot()  # Obtém o timeslot atual da rede
            timeslot_requests = []  # Requisições alocadas no timeslot atual

            for request in requests[:]:  # Itera sobre uma cópia da lista
                alice_id = request['alice_id']
                bob_id = request['bob_id']
                route = self.network.networklayer.short_route_valid(alice_id, bob_id)

                # Verifica se a rota está disponível
                if route and self.is_route_available(route):
                    # Marca a rota como ocupada e agenda a requisição
                    self.reserve_route(route, current_timeslot)
                    timeslot_requests.append((request, route))  # Salva a rota junto com a requisição
                    requests.remove(request)

            # Salva as requisições agendadas para o timeslot atual
            if timeslot_requests:
                self.scheduled_requests[current_timeslot] = timeslot_requests
                self.logger.log(f"Timeslot {current_timeslot}: {len(timeslot_requests)} requisições agendadas.")
                attempts = 0
            else:
                attempts += 1  # Incrementa as tentativas se nenhuma requisição foi alocada

            # Avança o timeslot na rede
            self.network.timeslot()

        if attempts >= max_attempts:
            self.logger.log(f"Parando o agendamento após {max_attempts} tentativas sem sucesso.")


    def is_route_available(self, route):
        """
        Verifica se a rota está disponível (não ocupada).
        """
        for i in range(len(route) - 1):
            link = (route[i], route[i + 1])
            if link in self.occupied_routes:
                self.logger.log(f"Rota {route} indisponível: link {link} já está reservado.")
                return False
        return True

    def reserve_route(self, route, timeslot):
        """
        Reserva uma rota para o protocolo.
        """
        for i in range(len(route) - 1):
            link = (route[i], route[i + 1])
            self.occupied_routes[link] = timeslot
        self.logger.log(f"Rota {route} reservada no timeslot {timeslot}.")


    def release_route(self, route):
        """
        Libera uma rota após o término do protocolo.
        """
        for i in range(len(route) - 1):
            link = (route[i], route[i + 1])
            if link in self.occupied_routes:
                del self.occupied_routes[link]
        self.logger.log(f"Rota {route} liberada.")


    def generate_schedule_report(self):
        """
        Gera um relatório detalhado do agendamento de requisições por timeslot.
        """
        if not self.scheduled_requests:
            print("Nenhuma requisição foi agendada.")
            return

        print("Relatório de Agendamento:")
        for timeslot, requests in self.scheduled_requests.items():
            print(f"Timeslot {timeslot}: {len(requests)} requisições alocadas.")
            for request, route in requests:  # Acessa o request e a rota
                print(f"  - Alice {request['alice_id']} -> Bob {request['bob_id']} | Protocolo: {request['protocol']}")
                print(f"    Rota reservada: {route}")


    def send_scheduled_requests(self):
        """
        Executa as requisições agendadas e libera as rotas após a execução.
        """
        self.logger.log("Iniciando execução de requisições agendadas.")

        for timeslot, requests in self.scheduled_requests.items():
            # Avança os timeslots na rede até alcançar o atual
            while self.network.get_timeslot() < timeslot:
                self.network.timeslot()
                self.logger.log(f"Timeslot avançado para {self.network.get_timeslot()}.")

            # Executa cada requisição no timeslot atual
            self.logger.log(f"Enviando requisições do timeslot {timeslot} para execução.")
            for request, route in requests:
                self.network.execute_request(request)  # Executa a requisição
                self.release_route(route)  # Libera a rota após a execução

    # def generate_schedule_report(self):
    #     """
    #     Gera um relatório detalhado do agendamento de requisições por timeslot.
    #     """
    #     if not self.scheduled_requests:
    #         print("Nenhuma requisição foi agendada.")
    #         return

    #     print("Relatório de Agendamento:")
    #     for timeslot, requests in self.scheduled_requests.items():
    #         print(f"Timeslot {timeslot}: {len(requests)} requisições alocadas.")
    #         for request in requests:
    #             print(f"  - Alice {request['alice_id']} -> Bob {request['bob_id']} | Protocolo: {request['protocol']}")


    # def release_route(self, route):
    #     """
    #     Libera uma rota após o término do protocolo.
    #     """
    #     for i in range(len(route) - 1):
    #         link = (route[i], route[i + 1])
    #         if link in self.occupied_routes:
    #             del self.occupied_routes[link]  # Remove a reserva
    #     self.logger.log(f"Rota {route} liberada.")

    
    # def receive_request(self, request):
    #     """
    #     Recebe uma nova requisição e adiciona à lista de requisições pendentes.
        
    #     Args:
    #         request (dict): Requisição contendo informações como Alice, Bob, circuito e qubits.
    #     """
    #     self.pending_requests.append(request)
    #     self.logger.log(f"Requisição recebida: {request}")


    # def schedule_requests(self, requests, max_attempts=10):
    #     """
    #     Agenda as requisições recebidas, maximizando o número de requisições processadas em um único timeslot,
    #     utilizando o timeslot diretamente da rede.
    #     """
    #     attempts = 0  # Contador de tentativas

    #     while requests and attempts < max_attempts:
    #         current_timeslot = self.network.get_timeslot()  # Obtém o timeslot atual da rede
    #         timeslot_requests = []  # Requisições alocadas no timeslot atual
    #         used_links = set()  # Arestas ocupadas no timeslot atual

    #         for request in requests[:]:  # Itera sobre uma cópia da lista
    #             alice_id = request['alice_id']
    #             bob_id = request['bob_id']
    #             route = self.network.networklayer.short_route_valid(alice_id, bob_id)

    #             if route and self.is_route_available(route, used_links):
    #                 timeslot_requests.append(request)
    #                 requests.remove(request)

    #                 # Marca as arestas da rota como usadas
    #                 for i in range(len(route) - 1):
    #                     used_links.add((route[i], route[i + 1]))

    #                 # Reserva a rota para o timeslot atual
    #                 self.reserve_route(route, current_timeslot)

    #         # Salva as requisições alocadas para o timeslot atual
    #         if timeslot_requests:
    #             self.scheduled_requests[current_timeslot] = timeslot_requests
    #             self.logger.log(f"Timeslot {current_timeslot}: {len(timeslot_requests)} requisições alocadas.")
    #             attempts = 0  # Reseta as tentativas ao alocar requisições
    #         else:
    #             attempts += 1  # Incrementa o contador de tentativas se nenhuma requisição foi alocada

    #         # Avança o timeslot na rede
    #         self.network.timeslot()

    #     if attempts >= max_attempts:
    #         self.logger.log(f"Parando o agendamento após {max_attempts} tentativas sem sucesso.")

    # def send_scheduled_requests(self):
    #     """
    #     Envia as requisições agendadas para a rede executar, utilizando o timeslot da rede.
    #     """
    #     self.logger.log("Iniciando execução de requisições agendadas.")
    #     for timeslot, requests in self.scheduled_requests.items():
    #         # Avança os timeslots na rede até alcançar o atual
    #         while self.network.get_timeslot() < timeslot:
    #             self.network.timeslot()
    #             self.logger.log(f"Timeslot avançado para {self.network.get_timeslot()}.")

    #         # Executa cada requisição no timeslot atual
    #         self.logger.log(f"Enviando requisições do timeslot {timeslot} para execução.")
    #         for request in requests:
    #             self.network.execute_request(request)

    # def send_scheduled_requests(self):
    #     """
    #     Envia as requisições alocadas para a rede executar.
    #     """
    #     self.logger.log("Iniciando execução de requisições agendadas.")
    #     for timeslot, requests in self.scheduled_requests.items():
    #         self.logger.log(f"Enviando requisições do timeslot {timeslot} para execução.")
            
    #         # Avança o timeslot da rede até o atual
    #         while self.network.get_timeslot() < timeslot:
    #             self.network.timeslot()
    #             self.logger.log(f"Timeslot avançado para {self.network.get_timeslot()}.")

    #         # Executa cada requisição no timeslot
    #         for request in requests:
    #             self.network.execute_request(request)
    
       # def is_route_available(self, route, used_links):
    #     """
    #     Verifica se uma rota está disponível, considerando os links já ocupados.

    #     Args:
    #         route (list): Lista de nós na rota.
    #         used_links (set): Conjunto de links ocupados.

    #     Returns:
    #         bool: True se a rota está disponível, False caso contrário.
    #     """
    #     for i in range(len(route) - 1):
    #         link = (route[i], route[i + 1])
    #         reverse_link = (route[i + 1], route[i])  # Verifica o link reverso também
    #         if link in used_links or reverse_link in used_links:
    #             self.logger.log(f"Rota {route} indisponível: link {link} já está em uso.")
    #             return False
    #     return True
    
    # def reserve_route(self, route, timeslot):
    #     """
    #     Reserva uma rota e marca como ocupada até o término do protocolo.
    #     """
    #     for i in range(len(route) - 1):
    #         link = (route[i], route[i + 1])
    #         self.occupied_routes[link] = timeslot  # Marca como ocupada
    #     self.logger.log(f"Rota {route} reservada no timeslot {timeslot} (Rede: {self.network.get_timeslot()}).")

    # def reserve_route(self, route, timeslot):
    #     """
    #     Reserva uma rota e marca como ocupada até o término do protocolo.
    #     """
    #     for i in range(len(route) - 1):
    #         link = (route[i], route[i + 1])
    #         self.occupied_routes[link] = timeslot  # Marca como ocupada
    #     self.logger.log(f"Rota {route} reservada no timeslot {timeslot} (Rede: {self.network.get_timeslot()}).")

    

    #  TODO :  ver a parte do código do arthur, alocar o protocolo pelo limite da topologia 
    # if not any(link in all_used_links for link in route_links):
                        # Se a app for BB84 ou B92, adiciona os links usados no conjunto de links usados apenas por essas apps
                        # if request.app == 'BB84' or request.app == 'B92':
                        #     bb84_b92_used_links.update(route_links)
                        
                        # # Adicionando as informações de rota, app e prioridade
                        # request.route = route
                        # info.append(request)
                        
                        # # Adiciona os links usados no conjunto de links usados
                        # all_used_links.update(route_links)
 
                        # break 