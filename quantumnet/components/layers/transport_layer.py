import networkx as nx
from quantumnet.components import Host
from quantumnet.objects import Logger, Epr
from random import uniform
import math

class TransportLayer:
    def __init__(self, network, network_layer, link_layer, physical_layer):
        """
        Inicializa a camada de transporte.
        
        args:
            network : Network : Rede.
            network_layer : NetworkLayer : Camada de rede.
            link_layer : LinkLayer : Camada de enlace.
            physical_layer : PhysicalLayer : Camada física.
        """
        self._network = network
        self._physical_layer = physical_layer
        self._network_layer = network_layer
        self._link_layer = link_layer
        self.logger = Logger.get_instance()
        self.transmitted_qubits = []
        self.used_eprs = 0
        self.used_qubits = 0
        self.created_eprs = []  # Lista para armazenar EPRs criados


    def __str__(self):
        """ Retorna a representação em string da camada de transporte. 
        
        returns:
            str : Representação em string da camada de transporte."""
        return f'Transport Layer'
    
    def get_used_eprs(self):
        self.logger.debug(f"Eprs usados na camada {self.__class__.__name__}: {self.used_eprs}")
        return self.used_eprs
    
    def get_used_qubits(self):
        self.logger.debug(f"Qubits usados na camada {self.__class__.__name__}: {self.used_qubits}")
        return self.used_qubits
    
    def request_transmission(self, alice_id: int, bob_id: int, num_qubits: int):
        """
        Requisição de transmissão de n qubits entre Alice e Bob.
        
        args:
            alice_id : int : Id do host Alice.
            bob_id : int : Id do host Bob.
            num_qubits : int : Número de qubits a serem transmitidos.
            
        returns:
            bool : True se a transmissão foi bem-sucedida, False caso contrário.
        """
        alice = self._network.get_host(alice_id)
        available_qubits = len(alice.memory)

        if available_qubits < num_qubits:
            self.logger.log(f'Número insuficiente de qubits na memória de Alice (Host:{alice_id}). Tentando transmitir os {available_qubits} qubits disponíveis.')
            num_qubits = available_qubits

        if num_qubits == 0:
            self.logger.log(f'Nenhum qubit disponível na memória de Alice ({alice_id}) para transmissão.')
            return False

        max_attempts = 2
        attempts = 0
        success = False

        while attempts < max_attempts and not success:
            self._network.timeslot()  # Incrementa o timeslot para cada tentativa de transmissão
            self.logger.log(f'Timeslot {self._network.get_timeslot()}: Tentativa de transmissão {attempts + 1} entre {alice_id} e {bob_id}.')
            
            routes = []
            for _ in range(num_qubits):
                route = self._network_layer.short_route_valid(alice_id, bob_id)
                if route is None:
                    self.logger.log(f'Não foi possível encontrar uma rota válida na tentativa {attempts + 1}. Timeslot: {self._network.get_timeslot()}')
                    break
                routes.append(route)
            
            if len(routes) == num_qubits:
                success = True
                for route in routes:
                    for i in range(len(route) - 1):
                        node1 = route[i]
                        node2 = route[i + 1]
                        # Verifica se há pelo menos um par EPR disponível no canal
                        if len(self._network.get_eprs_from_edge(node1, node2)) < 1:
                            self.logger.log(f'Falha ao encontrar par EPR entre {node1} e {node2} na tentativa {attempts + 1}. Timeslot: {self._network.get_timeslot()}')
                            success = False
                            break
                    if not success:
                        break
            
            if not success:
                attempts += 1

        if success:
            # Registrar os qubits transmitidos
            for route in routes:
                qubit_info = {
                    'route': route,
                    'alice_id': alice_id,
                    'bob_id': bob_id,
                }
                self.transmitted_qubits.append(qubit_info)
            self.logger.log(f'Transmissão de {num_qubits} qubits entre {alice_id} e {bob_id} concluída com sucesso. Timeslot: {self._network.get_timeslot()}')
            return True
        else:
            self.logger.log(f'Falha na transmissão de {num_qubits} qubits entre {alice_id} e {bob_id} após {attempts} tentativas. Timeslot: {self._network.get_timeslot()}')
            return False

    def teleportation_protocol(self, alice_id: int, bob_id: int):
        """
        Realiza o protocolo de teletransporte de um qubit de Alice para Bob.
        
        args:
            alice_id : int : Id do host Alice.
            bob_id : int : Id do host Bob.
        
        returns:
            bool : True se o teletransporte foi bem-sucedido, False caso contrário.
        """
        self._network.timeslot()  # Incrementa o timeslot para o protocolo de teletransporte
        self.logger.log(f'Timeslot {self._network.get_timeslot()}: Iniciando teletransporte entre {alice_id} e {bob_id}.')
        
        # Estabelece uma rota válida
        route = self._network_layer.short_route_valid(alice_id, bob_id)
        if route is None:
            self.logger.log(f'Não foi possível encontrar uma rota válida para teletransporte entre {alice_id} e {bob_id}. Timeslot: {self._network.get_timeslot()}')
            return False
        
        # Pega um qubit de Alice e um qubit de Bob
        alice = self._network.get_host(alice_id)
        bob = self._network.get_host(bob_id)
        
        if len(alice.memory) < 1 or len(bob.memory) < 1:
            self.logger.log(f'Alice ou Bob não possuem qubits suficientes para teletransporte. Timeslot: {self._network.get_timeslot()}')
            return False
        
        qubit_alice = alice.memory.pop(0)  # Remove o primeiro qubit da memória de Alice
        qubit_bob = bob.memory.pop()       # Remove o último qubit da memória de Bob
        
        # Calcula a fidelidade final do teletransporte
        f_alice = qubit_alice.get_current_fidelity()
        f_bob = qubit_bob.get_current_fidelity()
        
        # Assume fidelidade do link como a média das fidelidades dos pares EPR na rota
        fidelities = []
        for i in range(len(route) - 1):
            epr_pairs = self._network.get_eprs_from_edge(route[i], route[i+1])
            fidelities.extend([epr.get_current_fidelity() for epr in epr_pairs])
        
        if not fidelities:
            self.logger.log(f'Não foi possível encontrar pares EPR na rota entre {alice_id} e {bob_id}. Timeslot: {self._network.get_timeslot()}')
            return False
        
        f_route = sum(fidelities) / len(fidelities)
        
        # Fidelidade final do qubit teletransportado
        F_final = f_alice * f_bob * f_route + (1 - f_alice) * (1 - f_bob) * (1 - f_route)
        
        qubit_info = {
            'alice_id': alice_id,
            'bob_id': bob_id,
            'route': route,
            'fidelity_alice': f_alice,
            'fidelity_bob': f_bob,
            'fidelity_route': f_route,
            'F_final': F_final,
            'qubit_alice': qubit_alice,
            'qubit_bob': qubit_bob,
            'success': True
        }
        
        # Adiciona o qubit teletransportado à memória de Bob com a fidelidade final calculada
        qubit_alice.fidelity = F_final
        bob.memory.append(qubit_alice)
        self.logger.log(f'Teletransporte de qubit de {alice_id} para {bob_id} foi bem-sucedido com fidelidade final de {F_final}. Timeslot: {self._network.get_timeslot()}')
        
        # Par virtual é deletado no final
        for i in range(len(route) - 1):
            self._network.remove_epr(route[i], route[i + 1])
        
        self.transmitted_qubits.append(qubit_info)
        return True

    def avg_fidelity_on_transportlayer(self):
        """
        Calcula a fidelidade média de todos os qubits realmente utilizados na camada de transporte.

        returns:
            float : Fidelidade média dos qubits utilizados na camada de transporte.
        """
        total_fidelity = 0
        total_qubits_used = 0

        # Calcula a fidelidade dos qubits transmitidos e registrados no log de qubits transmitidos
        for qubit_info in self.transmitted_qubits:
            fidelity = qubit_info['F_final']
            total_fidelity += fidelity
            total_qubits_used += 1
            self.logger.log(f'Fidelidade do qubit utilizado de {qubit_info["alice_id"]} para {qubit_info["bob_id"]}: {fidelity}')

        # Considera apenas os qubits efetivamente transmitidos (não inclui os qubits que permanecem na memória dos hosts)
        if total_qubits_used == 0:
            self.logger.log('Nenhum qubit foi utilizado na camada de transporte.')
            return 0.0

        avg_fidelity = total_fidelity / total_qubits_used
        self.logger.log(f'A fidelidade média de todos os qubits utilizados na camada de transporte é {avg_fidelity}')
        
        return avg_fidelity


    def get_teleported_qubits(self):
        """
        Retorna a lista de qubits teletransportados.
        
        returns:
            list : Lista de dicionários contendo informações dos qubits teletransportados.
        """
        return self.transmitted_qubits
    
    def run_transport_layer(self, alice_id: int, bob_id: int, num_qubits: int, route=None):
        """
        Executa a requisição de transmissão e o protocolo de teletransporte.

        args:
            alice_id : int : Id do host Alice.
            bob_id : int : Id do host Bob.
            num_qubits : int : Número de qubits a serem transmitidos.

        returns:
            bool : True se a operação foi bem-sucedida, False caso contrário.
        """
        alice = self._network.get_host(alice_id)
        bob = self._network.get_host(bob_id)
        available_qubits = len(alice.memory)

        # Se Alice tiver menos qubits do que o necessário, crie mais qubits
        if available_qubits < num_qubits:
            qubits_needed = num_qubits - available_qubits
            for _ in range(qubits_needed):
                # self._network.timeslot()
                self._physical_layer.create_qubit(alice_id, increment_timeslot = False)
            available_qubits = len(alice.memory)

        if available_qubits != num_qubits:
            self.logger.log(f'Erro: Alice tem {available_qubits} qubits, mas deveria ter {num_qubits} qubits. Abortando transmissão.')
            return False

        max_attempts = 2
        attempts = 0
        success_count = 0
        route_fidelities = []  # Armazena fidelidades finais das rotas
        used_eprs = 0  # Contador de EPRs efetivamente utilizados na transmissão

        while attempts < max_attempts and success_count < num_qubits:
            for _ in range(num_qubits - success_count):
                # Usa a rota fornecida ou calcula uma nova rota, se necessário
                if route is None:
                    route = self._network_layer.short_route_valid(alice_id, bob_id)
                    if route is None:
                        self.logger.log(f'Não foi possível encontrar uma rota válida na tentativa {attempts + 1}.')
                        break
                else:
                    self.logger.log(f"Usando a rota fornecida: {route}")


                # Verifica a fidelidade dos pares EPR ao longo da rota
                fidelities = []
                eprs_used_in_current_transmission = 0  # Contador de EPRs para a rota atual
                for i in range(len(route) - 1):
                    node1 = route[i]
                    node2 = route[i + 1]
                    epr_pairs = self._network.get_eprs_from_edge(node1, node2)
                    
                    # Seleciona apenas os pares EPR necessários para a transmissão de um qubit
                    if epr_pairs:
                        fidelities.append(epr_pairs[0].get_current_fidelity())
                        eprs_used_in_current_transmission += 1
                    else:
                        self.logger.log(f'Não foi possível encontrar pares EPR suficientes na rota {route[i]} -> {route[i + 1]}.')
                        break
            
                if not fidelities:
                    attempts += 1
                    continue

                f_route = sum(fidelities) / len(fidelities)
                
                if alice.memory:
                    self._network.timeslot()
                    qubit_alice = alice.memory.pop(0)
                    f_alice = qubit_alice.get_current_fidelity()
                    
                    F_final = f_alice * f_route
                    route_fidelities.append(F_final)  # Adiciona a fidelidade final da rota à lista

                    qubit_alice.fidelity = F_final
                    bob.memory.append(qubit_alice)

                    success_count += 1
                    self.used_qubits += 1
                    used_eprs += eprs_used_in_current_transmission  # Conta EPRs usados apenas em transmissões bem-sucedidas
                    self.logger.log(f'Timeslot {self._network.get_timeslot()}: Teletransporte de qubit de {alice_id} para {bob_id} na rota {route} foi bem-sucedido com fidelidade final de {F_final}.')

                    self.transmitted_qubits.append({
                        'alice_id': alice_id,
                        'bob_id': bob_id,
                        'route': route,
                        'fidelity_alice': f_alice,
                        'fidelity_route': f_route,
                        'F_final': F_final,
                        'timeslot': self._network.get_timeslot(),
                        'qubit': qubit_alice
                    })
                else:
                    self.logger.log(f'Alice não possui qubits suficientes para continuar a transmissão.')
                    break

            attempts += 1

        # Passa a lista de fidelidades finais para a camada de aplicação
        self._network.application_layer.record_route_fidelities(route_fidelities)
        self._network.application_layer.record_used_eprs(used_eprs)  # Registra apenas EPRs usados na transmissão bem-sucedida

        if success_count == num_qubits:
            self.logger.log(f'Transmissão e teletransporte de {num_qubits} qubits entre {alice_id} e {bob_id} concluídos com sucesso.')
            return True
        else:
            self.logger.log(f'Falha na transmissão de {num_qubits} qubits entre {alice_id} e {bob_id}. Apenas {success_count} qubits foram transmitidos com sucesso.')
            return False


    def run_transport_layer_eprs(self, alice_id: int, bob_id: int, num_qubits: int, route=None):
        """
        Executa a requisição de transmissão e o protocolo de teletransporte.

        args:
            alice_id : int : Id do host Alice.
            bob_id : int : Id do host Bob.
            num_qubits : int : Número de qubits a serem transmitidos.

        returns:
            bool : True se a operação foi bem-sucedida, False caso contrário.
        """
        alice = self._network.get_host(alice_id)
        bob = self._network.get_host(bob_id)
        available_qubits = len(alice.memory)

        # Garantir qubits suficientes
        if available_qubits < num_qubits:
            qubits_needed = num_qubits - available_qubits
            for _ in range(qubits_needed):
                self._physical_layer.create_qubit(alice_id, increment_timeslot=False)
            available_qubits = len(alice.memory)

        if available_qubits != num_qubits:
            self.logger.log(f'Erro: Alice tem {available_qubits} qubits, mas deveria ter {num_qubits} qubits. Abortando transmissão.')
            return False

        max_attempts = 2
        attempts = 0
        success_count = 0
        route_fidelities = []
        used_eprs = 0
        total_eprs_used = 0

        while attempts < max_attempts and success_count < num_qubits:
            # Transmitir os qubits restantes
            while success_count < num_qubits:
                # Se a rota não for fornecida, calcule
                if route is None:
                    route = self._network_layer.short_route_valid(alice_id, bob_id,increment_timeslot=False)
                    if route is None:
                        self.logger.log(f'Não foi possível encontrar uma rota válida na tentativa {attempts + 1}.')
                        break
                else:
                    self.logger.log(f"Usando a rota fornecida: {route}")

                # Verificar fidelidade antes de usar EPRs
                f_route = self.calculate_average_fidelity(route)
                self.logger.log(f"Fidelidade atual da rota: {f_route}")

                # Se fidelidade < 0.8, recria EPRs
                if f_route < 0.85:
                    self.logger.log("Fidelidade abaixo de 0.8, recriando pares EPR de alta fidelidade.")
                    for i in range(len(route) - 1):
                        u, v = route[i], route[i+1]
                        # Remove todos os EPRs antigos
                        self._physical_layer.remove_all_eprs_from_channel((u, v))
                        # Cria novo EPR com fidelidade alta (0.99 por exemplo)
                        high_fidelity_epr = self._physical_layer.create_epr_pair(fidelity=0.99, increment_timeslot=False)
                        self._physical_layer.add_epr_to_channel(high_fidelity_epr, (u, v))

                    # Recalcular a fidelidade após recriação
                    f_route = self.calculate_average_fidelity(route)
                    self.logger.log(f"Nova fidelidade após recriação: {f_route}")

                    if f_route < 0.8:
                        self.logger.log("Mesmo após recriação, fidelidade continua baixa. Tentando novamente...")
                        attempts += 1
                        if attempts >= max_attempts:
                            # Falha definitiva
                            break
                        else:
                            continue  # Tentar novamente no próximo loop

                # Agora consumimos EPRs (fidelidade >= 0.8)
                fidelities = []
                eprs_used_in_current_transmission = 0
                # Consumir EPRs da rota
                for i in range(len(route) - 1):
                    node1 = route[i]
                    node2 = route[i + 1]
                    epr_pairs = self._network.get_eprs_from_edge(node1, node2)
                    epr_count = len(epr_pairs)
                    self.logger.log(f"Rota {node1} -> {node2} tem {epr_count} pares EPRs disponíveis.")

                    if epr_count > 0:
                        fidelities.append(epr_pairs[0].get_current_fidelity())
                        eprs_used_in_current_transmission += 1
                        total_eprs_used += 1
                        # Remove o EPR utilizado
                        self._network.remove_epr(node1, node2)
                    else:
                        self.logger.log(f'Não foi possível encontrar pares EPR suficientes na rota {node1} -> {node2}.')
                        # Neste caso, tenta novamente com outra rota ou recriação?
                        # Para simplificar, vamos aumentar attempts e romper:
                        attempts += 1
                        break

                if not fidelities:
                    if attempts >= max_attempts:
                        break
                    else:
                        continue

                f_route_used = sum(fidelities) / len(fidelities)

                # Teletransporta um qubit
                if alice.memory:
                    self._network.timeslot()
                    qubit_alice = alice.memory.pop(0)
                    f_alice = qubit_alice.get_current_fidelity()
        
                    F_final = f_alice * f_route_used
                    self.logger.log(f"Fidelidade final calculada: {F_final} (F_qubit: {f_alice} * F_rota: {f_route_used})")
                    route_fidelities.append(F_final)
                    qubit_alice.fidelity = F_final
                    bob.memory.append(qubit_alice)

                    success_count += 1
                    self.used_qubits += 1
                    used_eprs += eprs_used_in_current_transmission
                    self.logger.log(f'Timeslot {self._network.get_timeslot()}: Teletransporte de qubit de {alice_id} para {bob_id} na rota {route} foi bem-sucedido com fidelidade final de {F_final}.')

                    self.transmitted_qubits.append({
                        'alice_id': alice_id,
                        'bob_id': bob_id,
                        'route': route,
                        'fidelity_alice': f_alice,
                        'fidelity_route': f_route_used,
                        'F_final': F_final,
                        'timeslot': self._network.get_timeslot(),
                        'qubit': qubit_alice
                    })
                else:
                    self.logger.log('Alice não possui qubits suficientes.')
                    break

            attempts += 1

        # Registra fidelidades na camada de aplicação
        self._network.application_layer.record_route_fidelities(route_fidelities)
        self._network.application_layer.record_used_eprs(used_eprs)
        self.logger.log(f"Foram utilizados {total_eprs_used} pares EPRs ao longo da transmissão.")

        if success_count == num_qubits:
            self.logger.log(f'Transmissão e teletransporte de {num_qubits} qubits entre {alice_id} e {bob_id} concluídos com sucesso.')
            return True
        else:
            self.logger.log(f'Falha na transmissão de {num_qubits} qubits entre {alice_id} e {bob_id}. Apenas {success_count} qubits foram transmitidos com sucesso.')
            return False
        

    
    def calculate_average_fidelity(self, route):
        fidelities = []
        for i in range(len(route)-1):
            u, v = route[i], route[i+1]
            eprs = self._network.get_eprs_from_edge(u, v)
            if not eprs:
                self.logger.log(f"Sem pares EPR disponíveis no canal {u}->{v}. Fidelidade = 0.")
                return 0.0
            fidelity = eprs[-1].get_current_fidelity()  # Fidelidade do último EPR
            self.logger.log(f"Fidelidade do EPR {u}->{v}: {fidelity}")
            fidelities.append(fidelity)
        if fidelities:
            product = 1.0
            for f in fidelities:
                product *= f
            self.logger.log(f"Produto das fidelidades para rota {route}: {product}")
            return product
        return 0.0










































    # def run_transport_layer_eprs(self, alice_id: int, bob_id: int, num_qubits: int, route=None):
    #     alice = self._network.get_host(alice_id)
    #     bob = self._network.get_host(bob_id)
    #     available_qubits = len(alice.memory)

    #     # Garantir qubits suficientes
    #     if available_qubits < num_qubits:
    #         qubits_needed = num_qubits - available_qubits
    #         for _ in range(qubits_needed):
    #             self._physical_layer.create_qubit(alice_id, increment_timeslot=False)
    #         available_qubits = len(alice.memory)

    #     if available_qubits != num_qubits:
    #         self.logger.log(f'Erro: Alice tem {available_qubits} qubits, mas deveria ter {num_qubits} qubits. Abortando transmissão.')
    #         return False

    #     max_attempts = 2
    #     attempts = 0
    #     success_count = 0
    #     route_fidelities = []
    #     used_eprs = 0
    #     total_eprs_used = 0

    #     while attempts < max_attempts and success_count < num_qubits:
    #         # Transmitir os qubits restantes
    #         while success_count < num_qubits:
    #             # Se a rota não for fornecida, calcule
    #             if route is None:
    #                 route = self._network_layer.short_route_valid(alice_id, bob_id, increment_timeslot=False)
    #                 if route is None:
    #                     self.logger.log(f'Não foi possível encontrar uma rota válida na tentativa {attempts + 1}.')
    #                     break
    #             else:
    #                 self.logger.log(f"Usando a rota fornecida: {route}")

    #             # Criação inicial de pares EPR
    #             for i in range(len(route) - 1):
    #                 u, v = route[i], route[i + 1]
    #                 current_eprs = len(self._network.get_eprs_from_edge(u, v))
    #                 eprs_needed = max(0, num_qubits - current_eprs)  # Verifique quantos pares são necessários

    #                 if eprs_needed > 0:
    #                     self.logger.log(f"Criando {eprs_needed} pares EPR para o enlace {u} -> {v}.")
    #                     for _ in range(eprs_needed):
    #                         high_fidelity_epr = self._physical_layer.create_epr_pair(fidelity=0.99, increment_timeslot=False)
    #                         self._physical_layer.add_epr_to_channel(high_fidelity_epr, (u, v))
    #                 else:
    #                     self.logger.log(f"Enlace {u} -> {v} já possui pares EPR suficientes.")

                    
    #             # Verificar fidelidade antes de usar EPRs
    #             f_route = self.calculate_average_fidelity(route)
    #             self.logger.log(f"Fidelidade atual da rota: {f_route}")

    #             # Se fidelidade < 0.8, recria EPRs
    #             if f_route < 0.85:
    #                 self.logger.log("Fidelidade abaixo de 0.85, recriando pares EPR de alta fidelidade.")
    #                 for i in range(len(route) - 1):
    #                     u, v = route[i], route[i+1]
    #                     self._physical_layer.remove_all_eprs_from_channel((u, v))
    #                     for _ in range(num_qubits):
    #                         high_fidelity_epr = self._physical_layer.create_epr_pair(fidelity=0.99, increment_timeslot=False)
    #                         self._physical_layer.add_epr_to_channel(high_fidelity_epr, (u, v))

    #                 # Recalcular a fidelidade após recriação
    #                 f_route = self.calculate_average_fidelity(route)
    #                 self.logger.log(f"Nova fidelidade após recriação: {f_route}")

    #                 if f_route < 0.85:
    #                     self.logger.log("Mesmo após recriação, fidelidade continua baixa. Tentando novamente...")
    #                     attempts += 1
    #                     if attempts >= max_attempts:
    #                         break
    #                     else:
    #                         continue  # Tentar novamente no próximo loop

    #             # Consumir EPRs da rota
    #             fidelities = []
    #             eprs_used_in_current_transmission = 0
    #             for i in range(len(route) - 1):
    #                 node1 = route[i]
    #                 node2 = route[i + 1]
    #                 epr_pairs = self._network.get_eprs_from_edge(node1, node2)
    #                 epr_count = len(epr_pairs)

    #                 if epr_count == 0:
    #                     self.logger.log(f"Erro: Não há pares EPR disponíveis no enlace {node1} -> {node2}.")
    #                     return False  # Falha no teletransporte se não houver EPRs suficientes

    #                 fidelities.append(epr_pairs[0].get_current_fidelity())
    #                 self._network.remove_epr(node1, node2)  # Consuma um par EPR

    #             if not fidelities:
    #                 if attempts >= max_attempts:
    #                     break
    #                 else:
    #                     continue

    #             f_route_used = sum(fidelities) / len(fidelities)

    #             # Teletransporta um qubit
    #             if alice.memory:
    #                 self._network.timeslot()
    #                 qubit_alice = alice.memory.pop(0)
    #                 f_alice = qubit_alice.get_current_fidelity()

    #                 F_final = f_alice * f_route_used
    #                 self.logger.log(f"Fidelidade final calculada: {F_final} (F_qubit: {f_alice} * F_rota: {f_route_used})")
    #                 route_fidelities.append(F_final)
    #                 qubit_alice.fidelity = F_final
    #                 bob.memory.append(qubit_alice)

    #                 success_count += 1
    #                 self.used_qubits += 1
    #                 used_eprs += eprs_used_in_current_transmission
    #                 self.logger.log(f'Timeslot {self._network.get_timeslot()}: Teletransporte de qubit de {alice_id} para {bob_id} na rota {route} foi bem-sucedido com fidelidade final de {F_final}.')

    #                 self.transmitted_qubits.append({
    #                     'alice_id': alice_id,
    #                     'bob_id': bob_id,
    #                     'route': route,
    #                     'fidelity_alice': f_alice,
    #                     'fidelity_route': f_route_used,
    #                     'F_final': F_final,
    #                     'timeslot': self._network.get_timeslot(),
    #                     'qubit': qubit_alice
    #                 })
    #             else:
    #                 self.logger.log('Alice não possui qubits suficientes.')
    #                 break

    #         attempts += 1

    #     # Registra fidelidades na camada de aplicação
    #     self._network.application_layer.record_route_fidelities(route_fidelities)
    #     self._network.application_layer.record_used_eprs(used_eprs)
    #     self.logger.log(f"Foram utilizados {total_eprs_used} pares EPRs ao longo da transmissão.")

    #     if success_count == num_qubits:
    #         self.logger.log(f'Transmissão e teletransporte de {num_qubits} qubits entre {alice_id} e {bob_id} concluídos com sucesso.')
    #         return True
    #     else:
    #         self.logger.log(f'Falha na transmissão de {num_qubits} qubits entre {alice_id} e {bob_id}. Apenas {success_count} qubits foram transmitidos com sucesso.')
    #         return False


