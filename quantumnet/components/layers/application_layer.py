import random
from quantumnet.components import Host
from quantumnet.objects import Qubit, Logger

class ApplicationLayer:
    def __init__(self, network, transport_layer, network_layer, link_layer, physical_layer):
        self._network = network
        self._physical_layer = physical_layer
        self._network_layer = network_layer
        self._link_layer = link_layer
        self._transport_layer = transport_layer
        self.logger = Logger.get_instance()
        self.used_qubits = 0

    def __str__(self):
        return 'Application Layer'
    
    def get_used_qubits(self):
        self.logger.debug(f"Qubits usados na camada {self.__class__.__name__}: {self.used_qubits}")
        return self.used_qubits
    
    def run_app(self, app_name, *args):
        if app_name == "AC_BQC":
            alice_id, bob_id, num_qubits = args
            return self.run_andrew_childs_protocol(alice_id,bob_id, num_qubits)
        elif app_name == "QKD_E91":
            alice_id, bob_id, num_qubits = args
            return self.qkd_e91_protocol(alice_id,bob_id, num_qubits)
        elif app_name == "BFK_BQC":
            alice_id, bob_id, num_qubits, num_rounds = args
            return self.bfk_protocol(alice_id, bob_id, num_qubits, num_rounds)  # Remove duplicação de "self"
        else:
            self.logger.log(f"Aplicação não realizada ou não encontrada.")
            return False


    def run_andrew_childs_protocol(self, alice_id, bob_id, num_qubits):
        alice = self._network.get_host(alice_id)
        bob = self._network.get_host(bob_id)

        # Passo 1: Alice prepara qubits únicos
        qubits = [Qubit(qubit_id=random.randint(0, 1000)) for _ in range(num_qubits)]  # Alice cria qubits únicos
        self.logger.log(f"Alice criou {len(qubits)} qubits para a transmissão.")

        # Log dos qubits após criação (antes de enviar)
        for qubit in qubits:
            self.logger.log(f"Qubit {qubit.qubit_id} criado por Alice - Estado: {qubit._qubit_state}, Fase: {qubit._phase}")

        # Alice cria uma mensagem clássica com instruções para Bob
        operations_classical_message = [self.generate_random_operation() for _ in qubits]
        self.logger.log(f"Instruções clássicas enviadas por Alice: {operations_classical_message}")

        # Passo 2: Alice envia os qubits para Bob
        success = self._transport_layer.run_transport_layer(alice_id, bob_id, len(qubits))  # Transmite o número de qubits, não a lista
        if not success:
            self.logger.log("Falha ao enviar os qubits para o servidor (Bob).")
            return None
        self.logger.log(f"Alice enviou {len(qubits)} qubits para Bob.")

        # Passo 3: Bob aplica as operações recebidas de Alice
        for qubit, operation in zip(qubits, operations_classical_message):
            self.apply_operation_from_message(qubit, operation)
        self.logger.log("Bob aplicou as operações instruídas por Alice nos qubits.")

        # Log dos qubits após operações de Bob
        for qubit in qubits:
            self.logger.log(f"Qubit {qubit.qubit_id} após operações de Bob - Estado: {qubit._qubit_state}, Fase: {qubit._phase}")

        # Passo 4: Bob devolve os qubits para Alice
        success = self._transport_layer.run_transport_layer(bob_id, alice_id, len(qubits))  # Devolve o número de qubits
        if not success:
            self.logger.log(f"Falha ao devolver os qubits para Alice. Bob tinha {len(qubits)} qubits.")
            return None
        self.logger.log(f"Bob devolveu {len(qubits)} qubits para Alice.")

        # Log dos qubits após serem devolvidos para Alice
        for qubit in qubits:
            self.logger.log(f"Qubit {qubit.qubit_id} devolvido para Alice - Estado: {qubit._qubit_state}, Fase: {qubit._phase}")

        # Passo 5: Alice aplica decodificação com operações Clifford
        for qubit, operation in zip(qubits, operations_classical_message):
            self.apply_clifford_decoding(qubit, operation)
            self.logger.log(f"Alice aplicou a decodificação Clifford no qubit {qubit.qubit_id}.")

        # Verifique se o número de qubits está correto após a decodificação
        if len(qubits) == num_qubits:
            self.logger.log(f"Protocolo concluído com sucesso. Alice tem {len(qubits)} qubits decodificados.")
        else:
            self.logger.log(f"Erro: Alice tem {len(qubits)} qubits, mas deveria ter {num_qubits} qubits. Abortando.")
            return None

        return qubits

    def generate_random_operation(self):
        operations = ['X', 'Y', 'Z']
        return random.choice(operations)

    def apply_operation_from_message(self, qubit, operation):
        if operation == 'X':
            qubit.apply_x()
        elif operation == 'Y':
            qubit.apply_y()
        elif operation == 'Z':
            qubit.apply_z()

    def apply_clifford_decoding(self, qubit, operation):
        if operation == 'X':
            qubit.apply_x()
        elif operation == 'Y':
            qubit.apply_y()
        elif operation == 'Z':
            qubit.apply_z()
#KVGJDFOSṼKON LFKWJMFCE
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
        alice = self._network.get_host(alice_id)
        bob = self._network.get_host(bob_id)

        final_key = []

        while len(final_key) < num_bits:
            num_qubits = int((num_bits - len(final_key)) * 2)  # Calcula o número de qubits necessários
            self.used_qubits += num_qubits
            self.logger.log(f'Iniciando protocolo E91 com {num_qubits} qubits.')

            key = [random.choice([0, 1]) for _ in range(num_qubits)]  # Gera uma chave aleatória de bits
            bases_alice = [random.choice([0, 1]) for _ in range(num_qubits)]  # Gera bases de medição aleatórias para Alice
            qubits = self.prepare_e91_qubits(key, bases_alice)  # Prepara os qubits com base na chave e nas bases
            self.logger.log(f'Qubits preparados com a chave: {key} e bases: {bases_alice}')

            success = self._transport_layer.run_transport_layer(alice_id, bob_id, num_qubits)
            if not success:
                self.logger.log(f'Falha na transmissão dos qubits de Alice para Bob.')
                return None

            self._network.timeslot()  # Incrementa o timeslot após a transmissão
            self.logger.debug(f"Timeslot incrementado após transmissão: {self._network.get_timeslot()}")

            bases_bob = [random.choice([0, 1]) for _ in range(num_qubits)]  # Gera bases de medição aleatórias para Bob
            results_bob = self.apply_bases_and_measure_e91(qubits, bases_bob)  # Bob mede os qubits usando suas bases
            self.logger.log(f'Resultados das medições: {results_bob} com bases: {bases_bob}')

            common_indices = [i for i in range(len(bases_alice)) if bases_alice[i] == bases_bob[i]]  # Índices onde as bases coincidem
            self.logger.log(f'Índices comuns: {common_indices}')

            shared_key_alice = [key[i] for i in common_indices]  # Chave compartilhada gerada por Alice
            shared_key_bob = [results_bob[i] for i in common_indices]  # Chave compartilhada gerada por Bob

            for a, b in zip(shared_key_alice, shared_key_bob):
                if a == b and len(final_key) < num_bits:
                    final_key.append(a)

            self.logger.log(f"Chaves obtidas até agora: {final_key}")

            if len(final_key) >= num_bits:
                final_key = final_key[:num_bits]
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
        self._network.timeslot()
        self.logger.debug(f"Timeslot incrementado na função prepare_e91_qubits: {self._network.get_timeslot()}")
        qubits = []
        for bit, base in zip(key, bases):
            qubit = Qubit(qubit_id=random.randint(0, 1000))  # Cria um novo qubit com ID aleatório
            if bit == 1:
                qubit.apply_x()  # Aplica a porta X (NOT) ao qubit se o bit for 1
            if base == 1:
                qubit.apply_hadamard()  # Aplica a porta Hadamard ao qubit se a base for 1
            qubits.append(qubit)
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
        self._network.timeslot()
        self.logger.debug(f"Timeslot incrementado na função apply_bases_and_measure_e91: {self._network.get_timeslot()}")
        results = []
        for qubit, base in zip(qubits, bases):
            if base == 1:
                qubit.apply_hadamard()
            measurement = qubit.measure()
            results.append(measurement)
        return results

    
#  TODO: fazer o protocolo do andrews, BFK e do try2 e tentar abstrair algumas coisas e ultizar o qiskit 

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

        # Fase 1: Cliente prepara os qubits
        qubits = self.prepare_qubits(client_id, num_qubits)
        
        # Aqui, estamos passando o número de qubits para a camada de transporte, e não a lista de qubits
        success = self._transport_layer.run_transport_layer(client_id, server_id, num_qubits)
        if not success:
            self.logger.log(f"Falha ao transmitir qubits do cliente {client_id} para o servidor {server_id}.")
            return None

        # Fase 2: Servidor cria o estado de brickwork com os qubits recebidos
        success = self.create_brickwork_state(server_id, qubits)
        if not success:
            self.logger.log(f"Falha na criação do estado de brickwork no servidor {server_id}.")
            return None

        # Fase 3: Cliente instrui o servidor a medir os qubits em cada rodada
        measurement_results = self.run_computation(client_id, server_id, num_rounds, qubits)

        self.logger.log(f"Protocolo BFK concluído com sucesso. Resultados: {measurement_results}")
        return measurement_results


    def prepare_qubits(self, alice_id, num_qubits):
        client = self._network.get_host(alice_id)
        qubits = []
        for i in range(num_qubits):
            r_j = random.choice([0, 1])
            qubit = Qubit(qubit_id=random.randint(0, 1000))
            if r_j == 1:
                qubit.apply_x()
            qubits.append(qubit)
            self.logger.log(f"Qubit {qubit.qubit_id} preparado pelo cliente {alice_id}.")
        return qubits

    def create_brickwork_state(self, bob_id, qubits):
        server = self._network.get_host(bob_id)
        for i in range(len(qubits) - 1):
            self.apply_controlled_phase(qubits[i], qubits[i + 1])
        self.logger.log(f"Servidor {bob_id} criou um estado de brickwork com {len(qubits)} qubits.")
        return True

    def run_computation(self, alice_id, bob_id, num_rounds, qubits):
        client = self._network.get_host(alice_id)
        server = self._network.get_host(bob_id)
        measurement_results = []

        for round_num in range(num_rounds):
            theta = random.uniform(0, 2 * 3.14159)
            self.logger.log(f"Rodada {round_num + 1}: Cliente {alice_id} envia ângulo de medição {theta} ao servidor.")
            qubit = qubits[round_num]
            result = self._physical_layer.measure_qubit_in_basis(qubit, theta)
            measurement_results.append(result)
            self.logger.log(f"Servidor {bob_id} mediu o qubit {qubit.qubit_id} e obteve {result}.")
            adjusted_theta = self.adjust_measurement_basis(theta, result)
            self.logger.log(f"Cliente {alice_id} ajustou a próxima base de medição para {adjusted_theta}.")

        return measurement_results

    def adjust_measurement_basis(self, theta, result):
        delta = 0.1
        if result == 1:
            return theta + delta
        else:
            return theta - delta