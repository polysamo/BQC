import random
import math

class Qubit():
    def __init__(self, qubit_id: int, initial_fidelity: float = None) -> None:
        self.qubit_id = qubit_id
        self._qubit_state = 0  # Define o estado inicial do qubit como 0
        self._phase = 1  # 1 para estado normal, -1 para estado com fase invertida (representa o efeito de Z)
        self._initial_fidelity = initial_fidelity if initial_fidelity is not None else random.uniform(0, 1)
        self._current_fidelity = self._initial_fidelity

    def __str__(self):
        return f"Qubit {self.qubit_id} with state {self._qubit_state} and phase {self._phase}"

    def update_fidelity(self):
        self._current_fidelity = random.uniform(0, 1)

    def get_initial_fidelity(self):
        return self._initial_fidelity

    def get_current_fidelity(self):
        return self._current_fidelity

    def set_current_fidelity(self, new_fidelity: float):
        """Define a fidelidade atual do qubit."""
        self._current_fidelity = new_fidelity

    def apply_x(self):
        """Aplica a porta X (NOT) ao qubit."""
        self._qubit_state = 1 if self._qubit_state == 0 else 0

    def apply_y(self):
        """Aplica a porta Y ao qubit."""
        # Porta Y transforma |0> em i|1> e |1> em -i|0>.
        # Como estamos simulando, invertemos o estado e consideramos a fase imaginária.
        self._qubit_state = 1 if self._qubit_state == 0 else 0
        self._phase *= -1  # Representa a rotação de fase imaginária

    def apply_z(self):
        """Aplica a porta Z ao qubit."""
        # Porta Z transforma |0> em |0> e |1> em -|1>.
        # Simulamos mudando apenas a fase quando o estado é |1>.
        if self._qubit_state == 1:
            self._phase *= -1  # Representa a inversão de fase do estado |1>

    def apply_hadamard(self):
        """Aplica a porta Hadamard (H) ao qubit."""
        # Hadamard transforma o estado |0> em (|0> + |1>) / sqrt(2)
        # e |1> em (|0> - |1>) / sqrt(2). Para simulação, usa-se probabilidade.
        if self._qubit_state == 0:
            self._qubit_state = random.choice([0, 1])  # Simula a superposição
        else:
            self._qubit_state = random.choice([0, 1])  # Simula a superposição
        # Alteração de fase com 50% de chance simula o comportamento quântico
        self._phase = random.choice([1, -1])

    def measure(self):
        """Realiza a medição do qubit no estado atual."""
        return self._qubit_state
