import networkx as nx
from ..objects import Logger, Qubit
from ..components import *
from .layers import *
import random
import os
import csv
import matplotlib.pyplot as plt


class Network():
    """
    Um objeto para utilizar como rede.
    """
    def __init__(self) -> None:
        # Sobre a rede
        self._graph = nx.Graph()
        self._topology = None
        self._hosts = {}
        self.node_colors = []
        # Camadas
        self._physical = PhysicalLayer(self)
        self._link = LinkLayer(self, self._physical)
        self._network = NetworkLayer(self, self._link, self._physical)
        self._transport = TransportLayer(self, self._network, self._link, self._physical)
        self._application = ApplicationLayer(self, self._transport, self._network, self._link, self._physical)
        # Sobre a execução
        self.logger = Logger.get_instance()
        self.count_qubit = 0
        #minimo e maximo
        self.max_prob = 1
        self.min_prob = 0.2
        self.timeslot_total = 0
        self.qubit_timeslots = {}  # Dicionário para armazenar qubits criados e seus timeslots

    @property
    def hosts(self):
        """
        Dicionário com os hosts da rede. No padrão {host_id: host}.

        Returns:
            dict : Dicionário com os hosts da rede.
        """
        return self._hosts
    
    @property
    def graph(self):
        """
        Grafo da rede.

        Returns:
            nx.Graph : Grafo da rede.
        """
        return self._graph
    
    @property
    def nodes(self):
        """
        Nós do grafo da rede.

        Returns:
            list : Lista de nós do grafo.
        """
        return self._graph.nodes()
    
    @property
    def edges(self):
        """
        Arestas do grafo da rede.

        Returns:
            list : Lista de arestas do grafo.
        """
        return self._graph.edges()
    
    # Camadas
    @property
    def physical(self):
        """
        Camada física da rede.

        Returns:
            PhysicalLayer : Camada física da rede.
        """
        return self._physical
    
    @property
    def linklayer(self):
        """
        Camada de enlace da rede.

        Returns:
            LinkLayer : Camada de enlace da rede.
        """
        return self._link
    
    @property 
    def networklayer(self):
        """
        Camada de rede da rede.

        Returns:
            NetworkLayer : Camada de rede da rede.
        """
        return self._network
    
    @property   
    def transportlayer(self):
        """
        Camada de transporte de transporte.

        Returns:
            TransportLayer : Camada de transporte de transporte.
        """
        return self._transport
    
    @property
    def application_layer(self):
        """
        Camada de transporte de aplicação.

        Returns:
            ApplicationLayer : Camada de aplicação.
        """
        return self._application

    def draw(self):
        """
        Desenha a rede.
        """
        nx.draw(self._graph, with_labels=True)
    
    def add_host(self, host: Host):
        """
        Adiciona um host à rede no dicionário de hosts, e o host_id ao grafo da rede.
            
        Args:
            host (Host): O host a ser adicionado.
        """
        # Adiciona o host ao dicionário de hosts, se não existir
        if host.host_id not in self._hosts:        
            self._hosts[host.host_id] = host
            Logger.get_instance().debug(f'Host {host.host_id} adicionado aos hosts da rede.')
        else:
            raise Exception(f'Host {host.host_id} já existe nos hosts da rede.')
            
        # Adiciona o nó ao grafo da rede, se não existir
        if not self._graph.has_node(host.host_id):
            self._graph.add_node(host.host_id)
            Logger.get_instance().debug(f'Nó {host.host_id} adicionado ao grafo da rede.')
            
        # Adiciona as conexões do nó ao grafo da rede, se não existirem
        for connection in host.connections:
            if not self._graph.has_edge(host.host_id, connection):
                self._graph.add_edge(host.host_id, connection)
                Logger.get_instance().debug(f'Conexões do {host.host_id} adicionados ao grafo da rede.')
    
    def get_host(self, host_id: int) -> Host:
        """
        Retorna um host da rede.

        Args:
            host_id (int): ID do host a ser retornado.

        Returns:
            Host : O host com o host_id fornecido.
        """
        return self._hosts[host_id]

    def get_eprs(self):
        """
        Cria uma lista de qubits entrelaçados (EPRs) associadas a cada aresta do grafo.

        Returns:
            Um dicionários que armazena as chaves que são as arestas do grafo e os valores são as
              listas de qubits entrelaçados (EPRs) associadas a cada aresta. 
        """
        eprs = {}
        for edge in self.edges:
            eprs[edge] = self._graph.edges[edge]['eprs']
        return eprs
    
    def get_eprs_from_edge(self, alice: int, bob: int) -> list:
        """
        Retorna os EPRs de uma aresta específica.

        Args:
            alice (int): ID do host Alice.
            bob (int): ID do host Bob.
        Returns:
            list : Lista de EPRs da aresta.
        """
        edge = (alice, bob)
        return self._graph.edges[edge]['eprs']
    
    def remove_epr(self, alice: int, bob: int) -> list:
        """
        Remove um EPR de um canal.

        Args:
            channel (tuple): Canal de comunicação.
        """
        channel = (alice, bob)
        try:
            epr = self._graph.edges[channel]['eprs'].pop(-1)   
            return epr
        except IndexError:
            raise Exception('Não há Pares EPRs.')   
        
    def set_ready_topology(self, topology_name: str, num_clients: int, *args: int) -> None:
        """
        Cria um grafo com uma topologia pronta e inicializa os nós como servidor, clientes e normais.

        Args:
            topology_name (str): Nome da topologia.
            num_clients (int): Número de nós que serão clientes.
            *args (int): Argumentos para a topologia, geralmente o número de nós totais.
        """
        # Converter o nome da topologia para minúsculas para aceitar qualquer variação de letras
        topology_name = topology_name.lower()

        # Cria a topologia conforme o nome
        if topology_name == 'grade':
            if len(args) != 2:
                raise Exception('Para a topologia Grade, são necessários dois argumentos.')
            self._graph = nx.grid_2d_graph(*args)
        elif topology_name == 'linha':
            if len(args) != 1:
                raise Exception('Para a topologia Linha, é necessário um argumento.')
            self._graph = nx.path_graph(*args)
        elif topology_name == 'anel':
            if len(args) != 1:
                raise Exception('Para a topologia Anel, é necessário um argumento.')
            self._graph = nx.cycle_graph(*args)

        # Converte os labels dos nós para inteiros
        self._graph = nx.convert_node_labels_to_integers(self._graph)

        total_nodes = len(self._graph.nodes())
        self.node_colors = []  # Armazena as cores dos nós

        # Inicializa o primeiro nó como servidor (cor verde)
        self._hosts[0] = ServerNode(0)
        self.node_colors.append('green')

        # Inicializa os próximos nós como clientes (cor vermelha)
        for node in range(1, num_clients + 1):
            self._hosts[node] = ClientNode(node)
            self.node_colors.append('red')

        # Inicializa os nós restantes como regulares (cor azul)
        for node in range(num_clients + 1, total_nodes):
            self._hosts[node] = RegularNode(node)
            self.node_colors.append('#1f78b8')

        # Inicia os hosts, canais e pares EPRs
        self.start_hosts()
        self.start_channels()
        self.start_eprs()


    def draw(self):
        node_colors = [self._hosts[node].color() for node in self._graph.nodes()]
        nx.draw(self._graph, with_labels=True, node_color=node_colors, node_size=800)
        plt.show()


    def start_hosts(self, num_qubits: int = 0):
        """
        Inicializa os hosts da rede com exceção do servidor (host 0).

        Args:
            num_qubits (int): Número de qubits a serem inicializados para cada host, exceto o host 0 (servidor).
        """
        for host_id in self._hosts:
            # Evita que o servidor (host 0) receba qubits
            if host_id == 0:
                self.logger.log(f"Host {host_id} é o servidor, não receberá qubits.")
                continue
            
            # Inicializa os qubits para os demais hosts
            for i in range(num_qubits):
                self.physical.create_qubit(host_id, increment_timeslot=False, increment_qubits=False)
            self.logger.log(f"Host {host_id} inicializado com {num_qubits} qubits.")
        
        print("Hosts inicializados")


    
    # def start_hosts(self, num_qubits: int = 10):
    #     """
    #     Inicializa os hosts da rede.
        
    #     Args:
    #         num_qubits (int): Número de qubits a serem inicializados.
    #     """
    #     for host_id in self._hosts:
    #         for i in range(num_qubits):
    #             self.physical.create_qubit(host_id, increment_timeslot=False,increment_qubits=False)
    #     print("Hosts inicializados")    

    def start_channels(self):
        """
        Inicializa os canais da rede.
        
        Args:
            prob_on_demand_epr_create (float): Probabilidade de criar um EPR sob demanda.
            prob_replay_epr_create (float): Probabilidade de criar um EPR de replay.
        """
        for edge in self.edges:
            self._graph.edges[edge]['prob_on_demand_epr_create'] = random.uniform(self.min_prob, self.max_prob)
            self._graph.edges[edge]['prob_replay_epr_create'] = random.uniform(self.min_prob, self.max_prob)
            self._graph.edges[edge]['eprs'] = list()
        print("Canais inicializados")
        
    def start_eprs(self, num_eprs: int = 10):
        """
        Inicializa os pares EPRs nas arestas da rede.

        Args:
            num_eprs (int): Número de pares EPR a serem inicializados para cada canal.
        """
        for edge in self.edges:
            for i in range(num_eprs):
                epr = self.physical.create_epr_pair(increment_timeslot=False,increment_eprs=False)
                self._graph.edges[edge]['eprs'].append(epr)
                self.logger.debug(f'Par EPR {epr} adicionado ao canal.')
        print("Pares EPRs adicionados")

        
    def timeslot(self):
        """
        Incrementa o timeslot da rede.
        """
        self.timeslot_total += 1
        self.apply_decoherence_to_all_layers()

    def get_timeslot(self):
        """
        Retorna o timeslot atual da rede.

        Returns:
            int : Timeslot atual da rede.
        """
        return self.timeslot_total

    def register_qubit_creation(self, qubit_id, timeslot):
        """
        Registra a criação de um qubit associando-o ao timeslot em que foi criado.
    
        Args:
            qubit_id (int): ID do qubit criado.
            timeslot (int): Timeslot em que o qubit foi criado.
        """
        self.qubit_timeslots[qubit_id] = {'timeslot': timeslot}
        
    def display_all_qubit_timeslots(self):
        """
        Exibe o timeslot de todos os qubits criados nas diferentes camadas da rede.
        Se nenhum qubit foi criado, exibe uma mensagem apropriada.
        """
        if not self.qubit_timeslots:
            print("Nenhum qubit foi criado.")
        else:
            for qubit_id, info in self.qubit_timeslots.items():
                print(f"Qubit {qubit_id} foi criado no timeslot {info['timeslot']}")
                
                
    def get_total_useds_eprs(self):
        """
        Retorna o número total de EPRs (pares entrelaçados) utilizados na rede.

        Returns:
            int: Total de EPRs usados nas camadas física, de enlace e de rede.
        """
        total_eprs = (self._physical.get_used_eprs()+
                      self._link.get_used_eprs() +
                      self._network.get_used_eprs()
        )
        return total_eprs
    
    def get_total_useds_qubits(self):
        """
        Retorna o número total de qubits utilizados em toda a rede.

        Returns:
            int: Total de qubits usados nas camadas física, de enlace, transporte e aplicação.
        """

        total_qubits = (self._physical.get_used_qubits() +
                        self._link.get_used_qubits() +
                        self._transport.get_used_qubits() +
                        self._application.get_used_qubits()
                     
        )
        return total_qubits

    def get_metrics(self, metrics_requested=None, output_type="csv", file_name="metrics_output.csv"):
            """
            Obtém as métricas da rede conforme solicitado e as exporta, printa ou armazena.
            
            Args:
                metrics_requested: Lista de métricas a serem retornadas (opcional). 
                                Se None, todas as métricas serão consideradas.
                output_type: Especifica como as métricas devem ser retornadas.
                            "csv" para exportar em arquivo CSV (padrão),
                            "print" para exibir no console,
                            "variable" para retornar as métricas em uma variável.
                file_name: Nome do arquivo CSV (usado somente quando output_type="csv").
            
            Returns:
                Se output_type for "variable", retorna um dicionário com as métricas solicitadas.
            """
            # Dicionário com todas as métricas possíveis
            available_metrics = {
                "Timeslot Total": self.get_timeslot(),
                "EPRs Usados": self.get_total_useds_eprs(),
                "Qubits Usados": self.get_total_useds_qubits(),
                "Fidelidade na Camada de Transporte": self.transportlayer.avg_fidelity_on_transportlayer(),
                "Fidelidade na Camada de Enlace": self.linklayer.avg_fidelity_on_linklayer(),
                "Média de Rotas": self.networklayer.get_avg_size_routes()
            }
            
            # Se não foram solicitadas métricas específicas, use todas
            if metrics_requested is None:
                metrics_requested = available_metrics.keys()
            
            # Filtra as métricas solicitadas
            metrics = {metric: available_metrics[metric] for metric in metrics_requested if metric in available_metrics}

            # Tratamento conforme o tipo de saída solicitado
            if output_type == "print":
                for metric, value in metrics.items():
                    print(f"{metric}: {value}")
            elif output_type == "csv":
                current_directory = os.getcwd()
                file_path = os.path.join(current_directory, file_name)
                with open(file_path, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(['Métrica', 'Valor'])
                    for metric, value in metrics.items():
                        writer.writerow([metric, value])
                print(f"Métricas exportadas com sucesso para {file_path}")
            elif output_type == "variable":
                return metrics
            else:
                raise ValueError("Tipo de saída inválido. Escolha entre 'print', 'csv' ou 'variable'.")

    def apply_decoherence_to_all_layers(self, decoherence_factor: float = 0.9):
        """
        Aplica decoerência a todos os qubits e EPRs nas camadas da rede que já avançaram nos timeslots.
        """
        current_timeslot = self.get_timeslot()

        # Aplicar decoerência nos qubits de cada host
        for host_id, host in self.hosts.items():
            for qubit in host.memory:
                creation_timeslot = self.qubit_timeslots[qubit.qubit_id]['timeslot']
                if creation_timeslot < current_timeslot:
                    current_fidelity = qubit.get_current_fidelity()
                    new_fidelity = current_fidelity * decoherence_factor
                    qubit.set_current_fidelity(new_fidelity)

        # Aplicar decoerência nos EPRs em todos os canais (arestas da rede)
        for edge in self.edges:
            if 'eprs' in self._graph.edges[edge]:
                for epr in self._graph.edges[edge]['eprs']:
                    current_fidelity = epr.get_current_fidelity()
                    new_fidelity = current_fidelity * decoherence_factor
                    epr.set_fidelity(new_fidelity)


    # SIMULAÇÃO DA REDE 

    def choose_clients_and_server(self):
        """
        Define o servidor como o nó 0 e seleciona 3 clientes aleatórios.

        Returns:
            tuple: Lista de clientes e ID do servidor.
        """
        clients = random.sample(range(1, 9), 3)  # Supondo que temos 9 nós e o nó 0 é o servidor
        server = 0
        return clients, server

    def allocate_routes(self, clients, server):
        """
        Aloca rotas para cada cliente acessar o servidor.

        Args:
            clientes (list): Lista de clientes.
            servidor (int): ID do servidor.

        Returns:
            dict: Dicionário de rotas alocadas para cada cliente.
        """
        rotas_alocadas = {}
        for client in clients:
            route = self.networklayer.short_route_valid(client, server)
            if route:
                self.logger.log(f"Rota alocada para o cliente {client} ao servidor {server}: {route}")
                rotas_alocadas[client] = route
            else:
                self.logger.log(f"Falha ao alocar rota para o cliente {client}")
        return rotas_alocadas

    def execute_protocols(self, clients, server, rotas_alocadas):
        """
        Executa os protocolos designados para cada cliente utilizando as rotas alocadas.

        Args:
            clientes (list): Lista de IDs de clientes.
            servidor (int): ID do servidor.
            rotas_alocadas (dict): Dicionário de rotas alocadas.
        """
        applications = ["AC_BQC", "BFK_BQC", "TRY2_BQC"]
        
        for client in clients:
            # Escolhe uma aplicação aleatória para cada cliente
            application = random.choice(applications)
            num_qubits = random.randint(3, 7)  # Escolhe um número de qubits aleatório

            # Verifica se a aplicação é BFK_BQC, que precisa de um argumento adicional (número de rodadas)
            if application == "BFK_BQC":
                num_rounds = random.randint(1, 5)
                comando = f'self.application_layer.run_app("{application}", {client}, {server}, {num_qubits}, {num_rounds})'
            else:
                comando = f'self.application_layer.run_app("{application}", {client}, {server}, {num_qubits})'
            
            self.logger.log(f"Executando {application} para o cliente {client} no servidor {server} com rota {rotas_alocadas[client]} e {num_qubits} qubits.")
            
            # Executa o comando da aplicação
            exec(comando)  # Executa o protocolo

            # Mantém o caminho ativo durante a execução
            self.logger.log(f"Cliente {client} mantém a rota {rotas_alocadas[client]} durante a execução do protocolo.")

    def simulation(self):
        """
        Função principal para simular o cenário com 1 servidor e 3 clientes acessando ao mesmo tempo.
        """
        # Selecionar clientes e servidor
        clients, server = self.choose_clients_and_server()

        # Alocar rotas para cada cliente
        rotas_alocadas = self.allocate_routes(clients, server)
        
        # Executar protocolos para cada cliente com as rotas alocadas
        self.execute_protocols(clients, server, rotas_alocadas)