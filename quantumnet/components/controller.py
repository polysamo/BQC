import networkx as nx
from ..components import Network, Host, Logger  # Importações necessárias
from qiskit import QuantumCircuit
import random
        #get profundidade (depht) do circuito
        #numero de timeslots passadod= deplth
class Controller():
    def __init__(self,network):
        self.network = network
        self.hosts = None
        self.links = None
        self.logger = Logger.get_instance()  # Obtém uma instância do logger para registrar eventos
        self.pending_requests = []  # Lista para armazenar as requisições recebidas
        self.scheduled_requests = {}  # Dicionário para armazenar requisições por timeslot


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
        
        Args:
            request (dict): Requisição contendo informações como Alice, Bob, circuito e qubits.
        """
        self.pending_requests.append(request)
        self.logger.log(f"Requisição recebida: {request}")


    def schedule_requests(self, requests, max_attempts=10):
        """
        Agenda as requisições recebidas, maximizando o número de requisições processadas em um único timeslot,
        respeitando a disponibilidade de caminhos. Evita loops infinitos com um limite de tentativas.
        
        Args:
            requests (list): Lista de requisições.
            max_attempts (int): Número máximo de tentativas de agendamento.
        """
        current_timeslot = 0  # Inicia com o primeiro timeslot disponível
        attempts = 0  # Contador de tentativas
        self.scheduled_requests = {}  # Armazena as requisições alocadas

        while requests and attempts < max_attempts:
            timeslot_requests = []  # Requisições alocadas no timeslot atual
            used_links = set()  # Arestas ocupadas no timeslot atual

            for request in requests[:]:  # Itera sobre uma cópia da lista
                alice_id = request['alice_id']
                bob_id = request['bob_id']
                route = self.calculate_shortest_route(alice_id, bob_id)

                # Verifica se a rota está disponível e os links não estão ocupados
                if route and self.is_route_available(route, used_links):
                    timeslot_requests.append(request)
                    requests.remove(request)

                    # Marca as arestas da rota como usadas
                    for i in range(len(route) - 1):
                        used_links.add((route[i], route[i + 1]))

                    # Reserva a rota para o timeslot atual
                    self.reserve_route(route, current_timeslot)

            # Salva as requisições alocadas para o timeslot atual
            if timeslot_requests:
                self.scheduled_requests[current_timeslot] = timeslot_requests
                self.logger.log(f"Timeslot {current_timeslot}: {len(timeslot_requests)} requisições alocadas.")
                attempts = 0  # Reseta as tentativas ao alocar requisições
            else:
                attempts += 1  # Incrementa o contador de tentativas se nenhuma requisição foi alocada

            current_timeslot += 1  # Incrementa o timeslot para a próxima rodada

        if attempts >= max_attempts:
            self.logger.log(f"Parando o agendamento após {max_attempts} tentativas sem sucesso.")


    def calculate_shortest_route(self, alice_id, bob_id):
        """
        Calcula a rota de menor custo entre dois nós da rede.
        Se a rota mais curta não estiver disponível, tenta alternativas.

        Args:
            alice_id (int): ID do nó de origem.
            bob_id (int): ID do nó de destino.

        Returns:
            list: Lista de nós que compõem a rota mais curta disponível.
        """
        try:
            route = nx.shortest_path(self.network.graph, source=alice_id, target=bob_id)
            return route
        except nx.NetworkXNoPath:
            self.logger.log(f"Nenhuma rota disponível de {alice_id} para {bob_id}.")
            return None

    def is_route_available(self, route, used_links):
        """
        Verifica se uma rota está disponível, considerando os links já ocupados.

        Args:
            route (list): Lista de nós na rota.
            used_links (set): Conjunto de links ocupados.

        Returns:
            bool: True se a rota está disponível, False caso contrário.
        """
        for i in range(len(route) - 1):
            link = (route[i], route[i + 1])
            reverse_link = (route[i + 1], route[i])  # Verifica o link reverso também
            if link in used_links or reverse_link in used_links:
                self.logger.log(f"Rota {route} indisponível: link {link} já está em uso.")
                return False
        return True

    def reserve_route(self, route, timeslot):
        """
        Reserva uma rota para um determinado timeslot.
        
        Args:
            route (list): Lista de nós que compõem a rota.
            timeslot (int): Timeslot em que a rota será reservada.
        """
        for node in route:
            self.network.reserve_link(node, timeslot)
        self.logger.log(f"Rota {route} reservada no timeslot {timeslot}.")
        

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
            for request in requests:
                print(f"  - Alice {request['alice_id']} -> Bob {request['bob_id']} | Protocolo: {request['protocol']}")

    def send_scheduled_requests(self):
        """
        Envia as requisições alocadas para a rede executar.
        """
        self.logger.log("Iniciando execução de requisições agendadas.")
        for timeslot, requests in self.scheduled_requests.items():
            self.logger.log(f"Enviando requisições do timeslot {timeslot} para execução.")
            
            # Avança o timeslot da rede até o atual
            while self.network.get_timeslot() < timeslot:
                self.network.timeslot()
                self.logger.log(f"Timeslot avançado para {self.network.get_timeslot()}.")

            # Executa cada requisição no timeslot
            for request in requests:
                self.network.execute_request(request)


    

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