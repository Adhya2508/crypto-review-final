import hashlib
import time
import math
from concurrent.futures import ThreadPoolExecutor
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes


# ─────────────────────────────────────────────
#  Key Derivation
#  K = Kp ⊕ H(Vind + Sv)
# ─────────────────────────────────────────────
def derive_key(master_key: bytes, slice_id: int, version: int = 1) -> bytes:
    """Derive a unique 16-byte AES key per slice."""
    payload = f"{slice_id}{version}".encode()
    h = hashlib.sha256(payload).digest()[:16]
    key = bytes(a ^ b for a, b in zip(master_key, h))
    return key


# ─────────────────────────────────────────────
#  AES-CTR Encryption / Decryption
# ─────────────────────────────────────────────
def encrypt_slice(data: bytes, key: bytes) -> bytes:
    """Encrypt a single slice using AES-CTR. Prepends 8-byte nonce."""
    nonce = get_random_bytes(8)
    cipher = AES.new(key, AES.MODE_CTR, nonce=nonce)
    ciphertext = cipher.encrypt(data)
    return nonce + ciphertext          # store nonce with ciphertext


def decrypt_slice(data: bytes, key: bytes) -> bytes:
    """Decrypt a single slice encrypted with encrypt_slice."""
    nonce = data[:8]
    ciphertext = data[8:]
    cipher = AES.new(key, AES.MODE_CTR, nonce=nonce)
    return cipher.decrypt(ciphertext)


# ─────────────────────────────────────────────
#  Parallel Encryption
# ─────────────────────────────────────────────
def _encrypt_one(args):
    sid, data, master = args
    key = derive_key(master, sid)
    ct = encrypt_slice(data, key)
    return sid, ct


def parallel_encrypt(slice_data: dict, master_key: bytes, workers: int = 4) -> dict:
    """Encrypt all slices in parallel. Returns {slice_id: ciphertext}."""
    tasks = [(sid, data, master_key) for sid, data in slice_data.items()]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(_encrypt_one, tasks))
    return {sid: ct for sid, ct in results}


def _decrypt_one(args):
    sid, ct, master = args
    key = derive_key(master, sid)
    return sid, decrypt_slice(ct, key)


def parallel_decrypt(enc_data: dict, master_key: bytes, workers: int = 4) -> dict:
    """Decrypt all slices in parallel. Returns {slice_id: plaintext}."""
    tasks = [(sid, ct, master_key) for sid, ct in enc_data.items()]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(_decrypt_one, tasks))
    return {sid: pt for sid, pt in results}


# ─────────────────────────────────────────────
#  Shannon Entropy
# ─────────────────────────────────────────────
def compute_entropy(data: bytes) -> float:
    """Compute Shannon entropy (bits per byte) of a byte string."""
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    n = len(data)
    entropy = 0.0
    for f in freq:
        if f > 0:
            p = f / n
            entropy -= p * math.log2(p)
    return round(entropy, 4)


# ─────────────────────────────────────────────
#  Unauthorized-access simulation
# ─────────────────────────────────────────────
def unauthorized_decrypt_attempt(enc_data: dict) -> dict:
    """
    Simulate an unauthorized user trying to decrypt without the master key.
    Returns garbage / raises deliberately to show failure.
    """
    results = {}
    fake_key = b'\x00' * 16          # wrong key
    for sid, ct in enc_data.items():
        try:
            garbage = decrypt_slice(ct, fake_key)
            results[sid] = {
                "status": "decrypted_garbage",
                "entropy": compute_entropy(garbage),
                "note": "Output is meaningless noise — wrong key used"
            }
        except Exception as e:
            results[sid] = {"status": "error", "detail": str(e)}
    return results
