import random
from quantumnet.components import Host
from quantumnet.objects import Qubit, Logger

class ApplicationLayer:
    def __init__(self, network, transport_layer, network_layer, link_layer, physical_layer):
        """
        Inicializa a camada de aplicação do protocolo QKD (Distribuição Quântica de Chaves).

        Args:
            network: objeto que representa a rede quântica.
            transport_layer: camada de transporte da rede.
            network_layer: camada de rede da rede.
            link_layer: camada de enlace da rede.
            physical_layer: camada física da rede.
        """
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
        """
        Retorna o número de qubits utilizados na camada de aplicação e registra a informação no logger.

        Returns:
            int: Número de qubits usados na camada de aplicação.
        """
        self.logger.debug(f"Qubits usados na camada {self.__class__.__name__}: {self.used_qubits}")
        return self.used_qubits
    
#  TODO: fazer o protocolo do andrews, BFK e do try2 e tentar abstrair algumas coisas e ultizar o qiskit 

 
    def run_app(self, app_name, *args):
        """
        Executa a aplicação desejada informando o nome fornecido.

        Args:
            app_name (str): O nome da aplicação a ser executada.
            *args: Argumentos variáveis para a aplicação específica, que são alice_id, bob_id e num_qubits.
        """
        if app_name == "QKD_E91":
            alice_id, bob_id, num_qubits = args
            return self.qkd_e91_protocol(alice_id,bob_id, num_qubits)
        elif app_name == "AC_BQC":
            alice_id, bob_id, num_qubits = args
            return self.run_andrew_childs_protocol(alice_id,bob_id, num_qubits)
        else:
            self.logger.log(f"Aplicação não realizada ou não encontrada.")
            return False
        
    def run_andrew_childs_protocol(self, alice_id, bob_id, num_qubits):
        """
        Implementa o protocolo onde Alice envia qubits únicos com informações clássicas, e Bob aplica operações.
        
        Args:
            alice_id (int): ID de Alice (cliente).
            bob_id (int): ID de Bob (servidor).
            num_qubits (int): Número de qubits a serem enviados.
        """
        alice = self._network.get_host(alice_id)
        bob = self._network.get_host(bob_id)

        # Passo 1: Alice prepara qubits únicos
        qubits = [Qubit(qubit_id=random.randint(0, 1000)) for _ in range(num_qubits)]  # Alice cria qubits únicos
        self.logger.log(f"Alice criou {len(qubits)} qubits.")

        # Alice aplica operações aleatórias e cria uma mensagem clássica com instruções para o servidor
        operations_classical_message = []  # Contém as instruções clássicas sobre as operações que o servidor deve aplicar
        for qubit in qubits:
            random_operation = self.apply_random_operation(qubit)  # Alice codifica o qubit com operação aleatória
            operations_classical_message.append(random_operation)  # Instrução para servidor
            self.logger.log(f"Alice aplicou {random_operation} no qubit {qubit.qubit_id}")

        # Verificação de contagem de qubits antes de enviar para Bob
        self.logger.log(f"Verificação de contagem: Alice tem {len(qubits)} qubits antes de enviar para Bob.")

        # Passo 2: Alice envia os qubits para Bob
        success = self._transport_layer.run_transport_layer(alice_id, bob_id, len(qubits))
        if not success:
            self.logger.log("Falha ao enviar os qubits para o servidor (Bob).")
            return None
        self.logger.log(f"Alice enviou {len(qubits)} qubits para Bob.")

        # Passo 3: Alice envia informações clássicas sobre quais operações Bob deve aplicar
        self.logger.log(f"Alice enviou as instruções clássicas: {operations_classical_message}.")

        # Passo 4: Bob aplica as operações conforme instruções de Alice, sem medir
        for qubit, operation in zip(qubits, operations_classical_message):
            self.apply_operation_from_message(qubit, operation)
        self.logger.log("Bob aplicou as operações instruídas por Alice nos qubits.")

        # Verificação de contagem de qubits após operações de Bob
        self.logger.log(f"Verificação de contagem: Bob tem {len(qubits)} qubits após aplicar as operações.")

        # Passo 5: Bob devolve os qubits para Alice
        success = self._transport_layer.run_transport_layer(bob_id, alice_id, len(qubits))
        if not success:
            self.logger.log(f"Falha ao devolver os qubits para Alice. Bob tinha {len(qubits)} qubits.")
            return None
        self.logger.log(f"Bob devolveu {len(qubits)} qubits para Alice.")

        # Verificação de contagem de qubits após devolução para Alice
        self.logger.log(f"Verificação de contagem: Alice tem {len(qubits)} qubits após receber de Bob.")

        # Passo 6: Alice aplica decodificação com operações Clifford
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
    
    def apply_random_operation(self, qubit):
        """
        Aplica uma operação quântica aleatória (X, Y, Z ) ao qubit.

        Args:
            qubit (Qubit): O qubit no qual aplicar a operação.

        Returns:
            str: A operação aplicada (para referência na decodificação).
        """
        operations = ['X', 'Y', 'Z', 'I']  # Conjunto de operações que Alice pode aplicar
        operation = random.choice(operations)
        if operation == 'X':
            qubit.apply_x()
        elif operation == 'Y':
            qubit.apply_y()
        elif operation == 'Z':
            qubit.apply_z()

        return operation

    def apply_operation_from_message(self, qubit, operation):
        """
        Aplica a operação recebida na mensagem clássica no servidor.
        O servidor só aplica a operação e não realiza medições.

        Args:
            qubit (Qubit): O qubit no qual aplicar a operação.
            operation (str): A operação que Bob deve aplicar (X, Y, Z ).
        """
        if operation == 'X':
            qubit.apply_x()
        elif operation == 'Y':
            qubit.apply_y()
        elif operation == 'Z':
            qubit.apply_z()
        # Outras operações podem ser adicionadas aqui conforme necessário

    def apply_clifford_decoding(self, qubit, operation):
        """
        Aplica a operação de decodificação usando portas Clifford com base na operação original de Alice.

        Args:
            qubit (Qubit): O qubit a ser decodificado.
            operation (str): A operação Pauli aplicada originalmente por Alice.
        """
        # Operações Pauli são autoinversas, mas aqui vamos simular que Alice está decodificando com operações Clifford
        if operation == 'X':
            qubit.apply_x()  # Aplica X para decodificar
        elif operation == 'Y':
            qubit.apply_y()  # Aplica Y para decodificar
        elif operation == 'Z':
            qubit.apply_z()  # Aplica Z para decodificar


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