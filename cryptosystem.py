import numpy as np
from typing import List, Dict, Tuple
import time

class LieAlgebra:
    def __init__(self, n: int):
        self.n = n

    def random_element(self) -> np.ndarray:
        """Generate a random element in sl(n, R)."""
        M = np.random.rand(self.n, self.n)
        return self.project(M)

    def project(self, M: np.ndarray) -> np.ndarray:
        """Project a matrix onto sl(n, R)."""
        return M - (np.trace(M) / self.n) * np.eye(self.n)

    def lie_bracket(self, A: np.ndarray, B: np.ndarray) -> np.ndarray:
        """Compute the Lie bracket [A, B] = AB - BA."""
        return np.dot(A, B) - np.dot(B, A)

    def exp(self, A: np.ndarray) -> np.ndarray:
        """Compute the matrix exponential."""
        return np.linalg.matrix_power(np.eye(self.n) + A + np.dot(A, A)/2, self.n)

    def log(self, A: np.ndarray) -> np.ndarray:
        """Compute the matrix logarithm."""
        return np.linalg.logm(A)

    def solve_lie_equation(self, s: np.ndarray, d: np.ndarray) -> np.ndarray:
        """Solve the equation [s, X] + X = d for X."""
        n = self.n
        S = np.kron(np.eye(n), s) - np.kron(s.T, np.eye(n))
        A = S + np.eye(n*n)
        b = d.flatten()
        x = np.linalg.solve(A, b)
        return x.reshape((n, n))

    def is_in_subalgebra(self, element: np.ndarray, subalgebra_basis: np.ndarray) -> bool:
        """Check if an element is in the subalgebra spanned by the given basis."""
        flat_element = element.flatten()
        flat_basis = subalgebra_basis.reshape(-1, self.n**2)
        try:
            np.linalg.lstsq(flat_basis.T, flat_element, rcond=None)[0]
            return True
        except np.linalg.LinAlgError:
            return False

    def generate_subalgebra(self, k: int) -> np.ndarray:
        """Generate a random k-dimensional subalgebra of sl(n, R)."""
        basis = np.array([self.random_element() for _ in range(k)])
        return basis

class CryptoSystem:
    def __init__(self, n: int, subalgebra_dim: int):
        self.lie_algebra = LieAlgebra(n)
        self.n = n
        self.subalgebra_dim = subalgebra_dim
        self.block_size = n * n  # Number of bytes per block

    def generate_keys(self) -> Dict[str, np.ndarray]:
        """Generate public and private keys."""
        public_key = self.lie_algebra.generate_subalgebra(self.subalgebra_dim)
        while True:
            private_key = self.lie_algebra.random_element()
            if not self.lie_algebra.is_in_subalgebra(private_key, public_key):
                break
        return {"public_key": public_key, "private_key": private_key}

    def pad_message(self, message: bytes) -> bytes:
        """Pad the message to be a multiple of block_size."""
        padding_length = self.block_size - (len(message) % self.block_size)
        return message + bytes([padding_length] * padding_length)

    def unpad_message(self, padded_message: bytes) -> bytes:
        """Remove the padding from the message."""
        padding_length = padded_message[-1]
        return padded_message[:-padding_length]

    def message_to_matrices(self, message: str) -> List[np.ndarray]:
        """Convert a message to a list of matrices."""
        message_bytes = message.encode('utf-8')
        padded_message = self.pad_message(message_bytes)
        matrices = []
        for i in range(0, len(padded_message), self.block_size):
            block = padded_message[i:i+self.block_size]
            matrix = np.frombuffer(block, dtype=np.uint8).reshape((self.n, self.n))
            matrices.append(matrix)
        return matrices

    def matrices_to_message(self, matrices: List[np.ndarray]) -> str:
        """Convert a list of matrices back to a message."""
        byte_arrays = [matrix.tobytes() for matrix in matrices]
        padded_message = b''.join(byte_arrays)
        unpadded_message = self.unpad_message(padded_message)
        return unpadded_message.decode('utf-8', errors='replace')

    def encrypt(self, message: str, public_key: np.ndarray) -> List[np.ndarray]:
        """Encrypt a message of arbitrary length."""
        matrices = self.message_to_matrices(message)
        encrypted_matrices = []
        for M in matrices:
            R = self.lie_algebra.project(M.astype(float) / 255)  # Normalize to [0, 1]
            r = self.lie_algebra.random_element()
            encrypted_matrices.append(self.lie_algebra.lie_bracket(r, R) + R)
        return encrypted_matrices

    def decrypt(self, encrypted_matrices: List[np.ndarray], private_key: np.ndarray) -> str:
        """Decrypt a message of arbitrary length."""
        decrypted_matrices = []
        for encrypted_matrix in encrypted_matrices:
            d = self.lie_algebra.lie_bracket(private_key, encrypted_matrix)
            R = self.lie_algebra.solve_lie_equation(private_key, d)
            M = (R + (np.trace(R) / self.n) * np.eye(self.n)) * 255  # Denormalize
            decrypted_matrices.append(np.clip(np.round(M), 0, 255).astype(np.uint8))
        return self.matrices_to_message(decrypted_matrices)

def run_tests(crypto_system: CryptoSystem, keys: Dict[str, np.ndarray]) -> None:
    """Run encryption and decryption tests with various message lengths."""
    test_messages = [
        "Short message for testing.",
        "A longer message that spans multiple blocks. " * 10,
        "Complex characters: Hello, 你好, Здравствуйте! 123 !@#$%^&*()"
    ]

    for i, message in enumerate(test_messages):
        print(f"\nTest {i+1}: Message length = {len(message)} characters")
        
        start_time = time.time()
        encrypted = crypto_system.encrypt(message, keys["public_key"])
        encryption_time = time.time() - start_time
        
        start_time = time.time()
        decrypted = crypto_system.decrypt(encrypted, keys["private_key"])
        decryption_time = time.time() - start_time
        
        print(f"Encryption time: {encryption_time:.3f} seconds")
        print(f"Decryption time: {decryption_time:.3f} seconds")
        print(f"Decryption successful: {message == decrypted}")

def main():
    np.random.seed(42)  # For reproducibility
    n = 56  # Dimension of the Lie algebra
    k = 8   # Dimension of the subalgebra for the public key
    
    print(f"Initializing cryptosystem with n={n}, k={k}")
    crypto_system = CryptoSystem(n, k)
    
    print("Generating keys...")
    start_time = time.time()
    keys = crypto_system.generate_keys()
    key_gen_time = time.time() - start_time
    print(f"Key generation time: {key_gen_time:.3f} seconds")
    
    run_tests(crypto_system, keys)

if __name__ == "__main__":
    main()