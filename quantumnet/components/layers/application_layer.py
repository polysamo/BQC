import random
import math
from quantumnet.components import Host
from quantumnet.objects import Qubit, Logger

class ApplicationLayer:
    def __init__(self, network, transport_layer, network_layer, link_layer, physical_layer):
        """
        Inicializa a camada de aplicação.
        
        args:
            network : Network : Rede.
            transport_layer : TransportLayer : Camada de Transporte 
            network_layer : NetworkLayer : Camada de rede.
            link_layer : LinkLayer : Camada de enlace.
            physical_layer : PhysicalLayer : Camada física.
        """
        self._network = network
        self._physical_layer = physical_layer
        self._network_layer = network_layer
        self._link_layer = link_layer
        self._transport_layer = transport_layer
        self.logger = Logger.get_instance()
        self.used_qubits = 0

    def __str__(self):
        """ Retorna a representação em string da camada de aplicação. 
        
        returns:
            str : Representação em string da camada de aplicação."""
        return 'Application Layer'
    
    def get_used_qubits(self):
        self.logger.debug(f"Qubits usados na camada {self.__class__.__name__}: {self.used_qubits}")
        return self.used_qubits
    
    def run_app(self, app_name, *args):
        """
        Executa um protocolo quântico com base no nome da aplicação fornecido.

        Args:
            app_name : str : Nome do protocolo a ser executado (QKD_E91, AC_BQC, BFK_BQC, TRY2_BQC).
            *args : Argumentos variáveis passados para o protocolo.

        Returns:
            Depende do protocolo executado (chaves, resultados de medição ou estados quânticos).
        """
        if app_name == "QKD_E91":
            alice_id, bob_id, num_qubits = args
            return self.qkd_e91_protocol(alice_id,bob_id, num_qubits)
        elif app_name == "AC_BQC":
            alice_id, bob_id, num_qubits = args
            return self.run_andrews_childs_protocol(alice_id,bob_id, num_qubits)
        elif app_name == "BFK_BQC":
            alice_id, bob_id, num_qubits, num_rounds = args
            return self.bfk_protocol(alice_id, bob_id, num_qubits, num_rounds) 
        elif app_name == "TRY2_BQC":
            alice_id, bob_id, num_qubits = args
            return self.run_try2_protocol(alice_id, bob_id, num_qubits)
        else:
            self.logger.log(f"Aplicação não realizada ou não encontrada.")
            return False
        
    # PROTOCOLO E91 - QKD 

    def qkd_e91_protocol(self, alice_id, bob_id, num_bits):
        """
        Implementa o protocolo E91 para a Distribuição Quântica de Chaves (QKD).

        Args:
            alice_id (int): ID do host de Alice.
            bob_id (int): ID do host de Bob.
            num_bits (int): Número de bits para a chave.

        Returns:
            list: Chave final gerada pelo protocolo, ou None se houver falha na transmissão.
        """
        alice = self._network.get_host(alice_id)  # Obtém o host de Alice
        bob = self._network.get_host(bob_id)  # Obtém o host de Bob

        final_key = []  # Inicializa a chave final

        while len(final_key) < num_bits:
            num_qubits = int((num_bits - len(final_key)) * 2)  # Calcula o número de qubits necessários
            self.used_qubits += num_qubits
            self.logger.log(f'Iniciando protocolo E91 com {num_qubits} qubits.')

            # Etapa 1: Alice prepara os qubits
            key = [random.choice([0, 1]) for _ in range(num_qubits)]  # Gera uma chave aleatória de bits
            bases_alice = [random.choice([0, 1]) for _ in range(num_qubits)]  # Gera bases de medição aleatórias para Alice
            qubits = self.prepare_e91_qubits(key, bases_alice)  # Prepara os qubits com base na chave e nas bases
            self.logger.log(f'Qubits preparados com a chave: {key} e bases: {bases_alice}')

            # Etapa 2: Transmissão dos qubits de Alice para Bob
            success = self._transport_layer.run_transport_layer(alice_id, bob_id, num_qubits)
            if not success:
                self.logger.log(f'Falha na transmissão dos qubits de Alice para Bob.')
                return None

            self._network.timeslot()  # Incrementa o timeslot após a transmissão
            self.logger.debug(f"Timeslot incrementado após transmissão: {self._network.get_timeslot()}")

            # Etapa 3: Bob escolhe bases aleatórias e mede os qubits
            bases_bob = [random.choice([0, 1]) for _ in range(num_qubits)]  # Gera bases de medição aleatórias para Bob
            results_bob = self.apply_bases_and_measure_e91(qubits, bases_bob)  # Bob mede os qubits usando suas bases
            self.logger.log(f'Resultados das medições: {results_bob} com bases: {bases_bob}')

            # Etapa 4: Alice e Bob compartilham suas bases e encontram os índices comuns
            common_indices = [i for i in range(len(bases_alice)) if bases_alice[i] == bases_bob[i]]  # Índices onde as bases coincidem
            self.logger.log(f'Índices comuns: {common_indices}')

            # Etapa 5: Extração da chave com base nos índices comuns
            shared_key_alice = [key[i] for i in common_indices]  # Chave compartilhada gerada por Alice
            shared_key_bob = [results_bob[i] for i in common_indices]  # Chave compartilhada gerada por Bob

            # Etapa 6: Verificação se as chaves coincidem
            for a, b in zip(shared_key_alice, shared_key_bob):
                if a == b and len(final_key) < num_bits:  # Limita o tamanho da chave final
                    final_key.append(a)

            self.logger.log(f"Chaves obtidas até agora: {final_key}")

            if len(final_key) >= num_bits:
                final_key = final_key[:num_bits]  # Garante que a chave final tenha o tamanho exato solicitado
                self.logger.log(f"Protocolo E91 bem-sucedido. Chave final compartilhada: {final_key}")
                return final_key

        return None

    def prepare_e91_qubits(self, key, bases):
        """
        Prepara os qubits de acordo com a chave e as bases fornecidas para o protocolo E91.

        Args:
            key (list): Chave contendo a sequência de bits.
            bases (list): Bases usadas para medir os qubits.

        Returns:
            list: Lista de qubits preparados.
        """
        self._network.timeslot()  # Incrementa o timeslot
        self.logger.debug(f"Timeslot incrementado na função prepare_e91_qubits: {self._network.get_timeslot()}")
        qubits = []
        for bit, base in zip(key, bases):
            qubit = Qubit(qubit_id=random.randint(0, 1000))  # Cria um novo qubit com ID aleatório
            if bit == 1:
                qubit.apply_x()  # Aplica a porta X (NOT) ao qubit se o bit for 1
            if base == 1:
                qubit.apply_hadamard()  # Aplica a porta Hadamard ao qubit se a base for 1
            qubits.append(qubit)  # Adiciona o qubit preparado à lista de qubits
        return qubits
    

    def apply_bases_and_measure_e91(self, qubits, bases):
        """
        Aplica as bases de medição e mede os qubits no protocolo E91.

        Args:
            qubits (list): Lista de qubits a serem medidos.
            bases (list): Lista de bases a serem aplicadas para a medição.

        Returns:
            list: Resultados das medições.
        """
        self._network.timeslot()  # Incrementa o timeslot
        self.logger.debug(f"Timeslot incrementado na função apply_bases_and_measure_e91: {self._network.get_timeslot()}")
        results = []
        for qubit, base in zip(qubits, bases):
            if base == 1:
                qubit.apply_hadamard()  # Aplica a porta Hadamard antes de medir, se a base for 1
            measurement = qubit.measure()  # Mede o qubit
            results.append(measurement)  # Adiciona o resultado da medição à lista de resultados
        return results
    
    #PROTOCOLO ANDREWS CHILDS - BQC

    def run_andrews_childs_protocol(self, alice_id, bob_id, num_qubits):
        """
        Executa o protocolo Andrew Childs, onde Alice prepara qubits, envia para Bob, e Bob realiza operações.

        Args:
            alice_id : int : ID de Alice (cliente).
            bob_id : int : ID de Bob (servidor).
            num_qubits : int : Número de qubits a serem preparados por Alice.

        Returns:
            list : Lista de qubits devolvidos para Alice após a execução do protocolo.
        """
        alice = self._network.get_host(alice_id)
        bob = self._network.get_host(bob_id)

        self.logger.log(f"Limpando a memória do servidor (Bob) antes de iniciar o protocolo.")
        bob.memory.clear()

        # O cliente prepara qubits únicos e armazena-os
        qubits = [Qubit(qubit_id=random.randint(0, 1000)) for _ in range(num_qubits)]  
        self.logger.log(f"Cliente criou {len(qubits)} qubits para a transmissão.")

        self.used_qubits += len(qubits)

        # Registrar o qubit no dicionário de timeslots
        for qubit in qubits:
            # Registrar o qubit com o timeslot atual
            self._network.qubit_timeslots[qubit.qubit_id] = {'timeslot': self._network.get_timeslot()}
            self.logger.log(f"Qubit {qubit.qubit_id} registrado no timeslot {self._network.get_timeslot()}")

        # Log dos qubits após criação (antes de enviar)
        for qubit in qubits:
            self.logger.log(f"Qubit {qubit.qubit_id} criado pelo Cliente - Estado: {qubit._qubit_state}, Fase: {qubit._phase}")

        # Armazena os qubits criados na memória do cliente temporariamente para o transporte
        alice.memory.extend(qubits)  # Coloca esses qubits na memória do cliente temporariamente

        # O cliente cria uma mensagem clássica com instruções para o servidor
        operations_classical_message = [self.generate_random_operation() for _ in qubits]
        self.logger.log(f"Instruções clássicas enviadas pelo Cliente: {operations_classical_message}")

        # O cliente envia os qubits para o servidor
        success = self._transport_layer.run_transport_layer(alice_id, bob_id, len(qubits))  # Transmite o número de qubits, não a lista
        if not success:
            self.logger.log("Falha ao enviar os qubits para o servidor.")
            return None

        # Remove os qubits da memória do cliente após o transporte
        for qubit in qubits:
            if qubit in alice.memory:
                alice.memory.remove(qubit)

        self.logger.log(f"Cliente enviou {len(qubits)} qubits para o Servidor.")

        # Verificar a memória do servidor após receber os qubits
        self.logger.log(f"Servidor tem {len(bob.memory)} qubits na memória após a recepção dos qubits do Cliente.")

        # O servidor aplica as operações recebidas do cliente
        for qubit, operation in zip(qubits, operations_classical_message):
            self.apply_operation_from_message(qubit, operation)
        self.logger.log("Servidor aplicou as operações instruídas pelo Cliente nos qubits.")

        # Log dos qubits após operações do servidor
        for qubit in qubits:
            self.logger.log(f"Qubit {qubit.qubit_id} após operações de Servidor - Estado: {qubit._qubit_state}, Fase: {qubit._phase}")

        # O servidor devolve os qubits para o cliente
        success = self._transport_layer.run_transport_layer(bob_id, alice_id, len(qubits))  # Devolve o número de qubits
        if not success:
            self.logger.log(f"Falha ao devolver os qubits para o cliente. O servidor tinha {len(qubits)} qubits.")
            return None

        # Colocar os qubits de volta na memória do cliente após a devolução
        alice.memory.extend(qubits)

        self.logger.log(f"Servidor devolveu {len(qubits)} qubits para o cliente.")

        # Remover os qubits da memória do servidor após a devolução
        for qubit in qubits:
            if qubit in bob.memory:
                bob.memory.remove(qubit)

        # Log dos qubits após serem devolvidos para o cliente
        for qubit in qubits:
            self.logger.log(f"Qubit {qubit.qubit_id} devolvido para o cliente - Estado: {qubit._qubit_state}, Fase: {qubit._phase}")

        # O cliente aplica decodificação com operações Clifford
        for qubit, operation in zip(qubits, operations_classical_message):
            self.apply_clifford_decoding(qubit, operation)
            self.logger.log(f"Cliente aplicou a decodificação Clifford no qubit {qubit.qubit_id}.")

        # Verifique se o número de qubits está correto após a decodificação
        if len(qubits) == num_qubits:
            self.logger.log(f"Protocolo concluído com sucesso. O cliente tem {len(qubits)} qubits decodificados.")
        else:
            self.logger.log(f"Erro: Cliente tem {len(qubits)} qubits, mas deveria ter {num_qubits} qubits.")
            return None

        return qubits


    def generate_random_operation(self):
        """
        Gera uma operação quântica aleatória (X, Y, Z).

        Returns:
            str : Operação escolhida aleatoriamente.
        """
        operations = ['X', 'Y', 'Z']
        return random.choice(operations)

    def apply_operation_from_message(self, qubit, operation):
        """
        Aplica a operação quântica especificada em um qubit.

        Args:
            qubit : Qubit : O qubit ao qual a operação será aplicada.
            operation : str : Operação (X, Y ou Z) a ser aplicada.
        """
        if operation == 'X':
            qubit.apply_x()
        elif operation == 'Y':
            qubit.apply_y()
        elif operation == 'Z':
            qubit.apply_z()

    def apply_clifford_decoding(self, qubit, operation):
        """
        Aplica a operação Clifford de decodificação em um qubit.

        Args:
            qubit : Qubit : O qubit ao qual a operação será aplicada.
            operation : str : Operação Clifford a ser aplicada (X, Y ou Z).
        """
        if operation == 'X':
            qubit.apply_x()
        elif operation == 'Y':
            qubit.apply_y()
        elif operation == 'Z':
            qubit.apply_z()

    # PROTOCOLO BFK - BQC

    def bfk_protocol(self, client_id, server_id, num_qubits, num_rounds):
        """
        Executa o protocolo BFK completo: cliente prepara qubits, servidor cria brickwork e cliente envia instruções.
        
        Args:
            client_id (int): ID do cliente.
            server_id (int): ID do servidor.
            num_qubits (int): Número de qubits preparados pelo cliente.
            num_rounds (int): Número de rodadas de computação.
            
        Returns:
            list: Resultados finais das medições realizadas pelo servidor.
        """
        self.logger.log(f"Iniciando protocolo BFK com {num_qubits} qubits e {num_rounds} rodadas de computação.")
        
        self.used_qubits += num_qubits

        # Cliente prepara os qubits
        qubits = self.prepare_qubits(client_id, num_qubits)
        
        # Passa o número de qubits para a camada de transporte
        success = self._transport_layer.run_transport_layer(client_id, server_id, num_qubits)
        if not success:
            self.logger.log(f"Falha ao transmitir qubits do cliente {client_id} para o servidor {server_id}.")
            return None

        # Servidor cria o estado de brickwork com os qubits recebidos
        success = self.create_brickwork_state(server_id, qubits)
        if not success:
            self.logger.log(f"Falha na criação do estado de brickwork no servidor {server_id}.")
            return None

        # Cliente instrui o servidor a medir os qubits em cada rodada
        measurement_results = self.run_computation(client_id, server_id, num_rounds, qubits)

        self.logger.log(f"Protocolo BFK concluído com sucesso. Resultados: {measurement_results}")
        return measurement_results

    def prepare_qubits(self, alice_id, num_qubits):
        """
        Prepara os qubits no cliente para o protocolo BFK.

        Args:
            alice_id (int): ID do cliente que prepara os qubits.
            num_qubits (int): Número de qubits a serem preparados.

        Returns:
            list: Lista de qubits preparados pelo cliente.
        """
        client = self._network.get_host(alice_id)
        qubits = []
        for i in range(num_qubits):
            r_j = random.choice([0, 1])  # Cliente gera um bit aleatório r_j
            qubit = Qubit(qubit_id=random.randint(0, 1000))  # Cria um qubit com ID aleatório
            if r_j == 1:
                qubit.apply_x()  # Aplica a porta X se r_j for 1 (inverte o estado do qubit)
            qubits.append(qubit)
            self.logger.log(f"Qubit {qubit.qubit_id} preparado pelo cliente {alice_id}.")
        return qubits

    def create_brickwork_state(self, bob_id, qubits):
        """
        O servidor cria o estado de brickwork (tijolo) utilizando os qubits recebidos.

        Args:
            bob_id (int): ID do servidor que cria o estado.
            qubits (list): Lista de qubits recebidos do cliente.

        Returns:
            bool: True se o estado de brickwork foi criado com sucesso, False caso contrário.
        """
        server = self._network.get_host(bob_id)
        # Aplica a fase controlada nos qubits para criar o estado de brickwork
        for i in range(len(qubits) - 1):
            control_qubit = qubits[i]  # Qubit de controle
            target_qubit = qubits[i + 1]  # Qubit alvo
            target_qubit.apply_controlled_phase(control_qubit)  # Aplica a fase controlada
        self.logger.log(f"Servidor {bob_id} criou um estado de brickwork com {len(qubits)} qubits.")
        return True

    def run_computation(self, alice_id, bob_id, num_rounds, qubits):
        """
        Cliente instrui o servidor a realizar medições nos qubits durante as rodadas de computação.

        Args:
            alice_id (int): ID do cliente que fornece instruções.
            bob_id (int): ID do servidor que realiza as medições.
            num_rounds (int): Número de rodadas de computação a serem executadas.
            qubits (list): Lista de qubits a serem medidos.

        Returns:
            list: Resultados das medições realizadas pelo servidor em cada rodada.
        """
        client = self._network.get_host(alice_id)
        server = self._network.get_host(bob_id)
        measurement_results = []

        num_rounds = min(num_rounds, len(qubits))

        for round_num in range(num_rounds):
            # Cliente escolhe um ângulo aleatório de medição
            theta = random.uniform(0, 2 * math.pi)
            self.logger.log(f"Rodada {round_num + 1}: Cliente {alice_id} envia ângulo de medição {theta} ao servidor.")
            
            # Servidor mede o qubit na base fornecida pelo ângulo
            qubit = qubits[round_num]
            result = qubit.measure_in_basis(theta)
            measurement_results.append(result)

            # Cliente ajusta a próxima base de medição de acordo com o resultado
            adjusted_theta = self.adjust_measurement_basis(theta, result)
            self.logger.log(f"Cliente {alice_id} ajustou a próxima base de medição para {adjusted_theta}.")

        return measurement_results

    def adjust_measurement_basis(self, theta, result):
        """
        Ajusta a base de medição para a próxima rodada, com base no resultado da medição atual.

        Args:
            theta (float): O ângulo de medição atual.
            result (int): Resultado da medição (0 ou 1).

        Returns:
            float: O ângulo ajustado para a próxima rodada de medição.
        """
        delta = 0.1 # Ajuste incremental
        if result == 1:
            return theta + delta # Ajusta para cima se o resultado foi 1
        else:
            return theta - delta # Ajusta para baixo se o resultado foi 0

    # PROTOCOLO TRY2 - BQC

    def run_try2_protocol(self, alice_id, bob_id, num_qubits):
        """
        Executa o protocolo Try2 completo: cliente prepara qubits, servidor realiza a tomografia.
        
        Args:
            alice_id (int): ID do cliente.
            bob_id (int): ID do servidor.
            num_qubits (int): Número de qubits preparados pelo cliente.
            
        Returns:
            list: Resultados finais das medições realizadas pelo servidor.
            dict: Estado original de cada qubit baseado no r_i.
        """
        self.logger.log(f"Iniciando protocolo Try2 com {num_qubits} qubits.")
        
        self.used_qubits += num_qubits
        
        # Cliente prepara os qubits e armazena os valores r_i
        qubits = []
        qubit_states = {}
        
        for i in range(num_qubits):
            r_i = random.choice([0, 1])  # O cliente gera um bit aleatório r_i
            qubit = Qubit(qubit_id=random.randint(0, 1000))  # Cria um qubit com ID aleatório
            if r_i == 1:
                qubit.apply_x()  # Aplica a inversão de estado se r_i for 1
            qubits.append(qubit)
            qubit_states[qubit.qubit_id] = r_i  # O estado original do qubit é armazenado
            
            self.logger.log(f"Qubit {qubit.qubit_id} preparado com r_i = {r_i} pelo cliente {alice_id}.")
        
        # Adiciona os qubits criados à memória de Alice e registra os timeslots
        alice = self._network.get_host(alice_id)
        for qubit in qubits:
            alice.memory.append(qubit)  # Adiciona o qubit à memória do cliente 
            # Registra o timeslot de criação no dicionário self.qubit_timeslots
            self._network.qubit_timeslots[qubit.qubit_id] = {
                'timeslot': self._network.get_timeslot(),  # Usa o timeslot atual da rede
                'fidelity': qubit.get_current_fidelity()
            }
            self.logger.log(f"Qubit {qubit.qubit_id} registrado com timeslot {self._network.get_timeslot()}.")

        self.logger.log(f"Alice agora tem {len(alice.memory)} qubits em sua memória.")
        
        # Verifica se o cliente tem qubits suficientes na memória
        available_qubits = len(alice.memory)

        if available_qubits < num_qubits:
            self.logger.log(f'Erro: Alice tem {available_qubits} qubits, mas deveria ter {num_qubits} qubits. Abortando transmissão.')
            return None, None

        # Transmite os qubits para o servidor
        success = self._transport_layer.run_transport_layer(alice_id, bob_id, num_qubits)
        if not success:
            self.logger.log(f"Falha ao transmitir qubits do cliente {alice_id} para o servidor {bob_id}.")
            return None, None
        
        # Servidor realiza a tomografia
        tomography_results = []
        for qubit in qubits:
            # O servidor realiza a tomografia (neste caso, mede a probabilidade de cada qubit estar em |0> ou |1>)
            p_0 = random.uniform(0, 1)  # Simulação da tomografia
            p_1 = 1 - p_0
            tomography_results.append((p_0, p_1))
        
        self.logger.log(f"Protocolo Try2 concluído com sucesso. Resultados da tomografia: {tomography_results}")
        
        # Cliente decodifica o estado original dos qubits com base em r_i
        decoded_states = {}
        for qubit, (p_0, p_1) in zip(qubits, tomography_results):
            original_state = qubit_states[qubit.qubit_id]
            if original_state == 0:
                decoded_states[qubit.qubit_id] = '|0⟩'
            else:
                decoded_states[qubit.qubit_id] = '|1⟩'
        
        self.logger.log(f"Estados originais dos qubits baseados em r_i: {decoded_states}")
        
        return tomography_results, decoded_states


    def prepare_mixed_qubits(self, client_id, num_qubits):
        """
        O cliente prepara qubits mistos aplicando uma inversão condicional com base em bits aleatórios.
        
        Args:
            client_id (int): ID do cliente.
            num_qubits (int): Número de qubits a serem preparados.
        
        Returns:
            list: Lista de qubits preparados.
        """
        client = self._network.get_host(client_id)
        qubits = []
        
        for i in range(num_qubits):
            r_i = random.choice([0, 1])  # Gera um bit aleatório r_i
            qubit = Qubit(qubit_id=random.randint(0, 1000))  # Cria um novo qubit
            
            if r_i == 1:
                qubit.apply_x()  # Aplica a porta X se r_i for 1 (inverte o estado do qubit)
            
            qubits.append(qubit)
            self.logger.log(f"Qubit {qubit.qubit_id} preparado com r_i = {r_i} pelo cliente {client_id}.")
        
        return qubits

    def perform_tomography(self, server_id, qubits):
        """
        O servidor realiza tomografia quântica nos qubits recebidos.
        
        Args:
            server_id (int): ID do servidor.
            qubits (list): Lista de qubits recebidos pelo servidor.
        
        Returns:
            list: Resultados da tomografia (probabilidade de cada qubit estar em |0> ou |1>).
        """
        server = self._network.get_host(server_id)
        results = []
        
        for qubit in qubits:
            # O servidor realiza uma estimativa tomográfica do estado do qubit
            prob_0 = random.uniform(0, 1)  # Estima a probabilidade do qubit estar em |0>
            prob_1 = 1 - prob_0  # Probabilidade de estar em |1>
            results.append((prob_0, prob_1))  # Armazena as probabilidades
        
        return results  



    