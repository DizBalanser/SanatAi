# Line-by-Line Code Explanation

## Scenario I: Diffie-Hellman Key Exchange

### Cell 1: Generate Sophie-Germain Prime

```python
number_bits = 256
```
**Explanation**: Set the security level to 256 bits. This means we want a prime number that has 256 binary digits.

```python
lower_bound = 2**(number_bits-1)
```
**Explanation**: Calculate the smallest 256-bit number (2^255). This ensures our prime will be exactly 256 bits long.

```python
upper_bound = 2**number_bits - 1
```
**Explanation**: Calculate the largest 256-bit number (2^256 - 1). This is the maximum value for our prime.

```python
p = 1
```
**Explanation**: Initialize `p` to 1. We'll use this variable to store our Sophie-Germain prime.

```python
while not is_prime(p):
```
**Explanation**: Keep looping until we find a valid Sophie-Germain prime.

```python
    q = random_prime(upper_bound, lbound=lower_bound)
```
**Explanation**: Generate a random prime number `q` between lower_bound and upper_bound.

```python
    p = 2*q + 1
```
**Explanation**: Calculate `p = 2q + 1`. If both `q` and `p` are prime, then `p` is a Sophie-Germain prime.

```python
print(f"Sophie-Germain prime p generated: {p}")
```
**Explanation**: Display the generated prime number.

```python
print(f"Bit length: {p.nbits()}")
```
**Explanation**: Show how many bits this prime has (should be 256 or 257).

---

### Cell 2: Define Group and Generator

```python
G = GF(p)
```
**Explanation**: Create a Galois Field (finite field) with `p` elements. This is the mathematical structure where we'll do our calculations. Elements are integers from 0 to p-1.

```python
g = G.primitive_element()
```
**Explanation**: Find a generator `g` of the multiplicative group. A generator means that powers of `g` can produce all non-zero elements in the field. This is crucial for DH security.

```python
print(f"Generator g: {g}")
```
**Explanation**: Display the generator value.

---

### Cell 3: Generate Private Keys and Public Signals

```python
# Alice
x_A = randint(2, p-2)
```
**Explanation**: 
- Alice chooses a random **secret** number `x_A`
- Range: from 2 to p-2 (avoiding 0, 1, and p-1 for security)
- This is Alice's **private key** - she NEVER shares this!

```python
S_A = g**x_A
```
**Explanation**: 
- Alice computes her **public signal**: `S_A = g^x_A mod p`
- This uses modular exponentiation (automatically done in GF(p))
- She will send `S_A` to Bob (this is safe to share publicly)

```python
# Bob
x_B = randint(2, p-2)
```
**Explanation**: Bob chooses his own random **secret** number `x_B` (his private key).

```python
S_B = g**x_B
```
**Explanation**: Bob computes his **public signal**: `S_B = g^x_B mod p`

```python
print(f"Alice's Public Signal (S_A): {S_A}")
print(f"Bob's Public Signal (S_B):   {S_B}")
```
**Explanation**: Display both public signals. These can be sent over an insecure channel.

---

### Cell 4: Key Exchange and Shared Secret

```python
# Alice computes shared secret using Bob's signal
K_A = S_B**x_A
```
**Explanation**: 
- Alice receives Bob's public signal `S_B`
- She computes: `K_A = S_B^x_A = (g^x_B)^x_A = g^(x_A * x_B) mod p`
- This is the **shared secret key**

```python
# Bob computes shared secret using Alice's signal
K_B = S_A**x_B
```
**Explanation**: 
- Bob receives Alice's public signal `S_A`
- He computes: `K_B = S_A^x_B = (g^x_A)^x_B = g^(x_A * x_B) mod p`
- Mathematical fact: `K_A = K_B` because `g^(x_A * x_B) = g^(x_B * x_A)`

```python
print(f"Alice's Derived Key: {K_A}")
print(f"Bob's Derived Key:   {K_B}")
```
**Explanation**: Show both keys (they should be identical).

```python
if K_A == K_B:
    print("SUCCESS: Alice and Bob have the same shared secret key.")
else:
    print("FAILURE: Keys do not match.")
```
**Explanation**: Verify that both parties derived the same key. This should ALWAYS be true in standard DH.

---

## Scenario II: Man-in-the-Middle Attack

### Cell 1: Charlie's Attack

```python
print("Charlie intercepts S_A and S_B.")
```
**Explanation**: Charlie can see all messages sent between Alice and Bob (he's on the network).

```python
x_C = randint(2, p-2)
```
**Explanation**: Charlie generates his own **secret** key `x_C`.

```python
S_C = g**x_C
```
**Explanation**: Charlie computes his own **public signal** `S_C = g^x_C`.

```python
K_AC_Alice = S_C**x_A
```
**Explanation**: 
- Alice thinks she's receiving Bob's signal, but it's actually `S_C` from Charlie
- Alice computes: `K_AC = S_C^x_A = g^(x_C * x_A)`
- This is the key Alice **thinks** she shares with Bob

```python
K_BC_Bob = S_C**x_B
```
**Explanation**: 
- Bob thinks he's receiving Alice's signal, but it's actually `S_C` from Charlie
- Bob computes: `K_BC = S_C^x_B = g^(x_C * x_B)`
- This is the key Bob **thinks** he shares with Alice

```python
K_AC_Charlie = S_A**x_C
```
**Explanation**: 
- Charlie computes the key he shares with Alice
- `K_AC_Charlie = S_A^x_C = g^(x_A * x_C)`
- This equals what Alice computed: `K_AC_Alice`

```python
K_BC_Charlie = S_B**x_C
```
**Explanation**: 
- Charlie computes the key he shares with Bob
- `K_BC_Charlie = S_B^x_C = g^(x_B * x_C)`
- This equals what Bob computed: `K_BC_Bob`

```python
if K_AC_Alice == K_AC_Charlie and K_BC_Bob == K_BC_Charlie:
    print("ATTACK SUCCESS: Charlie has established separate keys with Alice and Bob.")
```
**Explanation**: 
- Verify Charlie successfully shares keys with both parties
- Charlie can now decrypt messages from Alice (using `K_AC`), read them, modify them, and re-encrypt for Bob (using `K_BC`)

```python
if K_AC_Alice != K_BC_Bob:
    print("Alice and Bob do NOT share the same key.")
```
**Explanation**: The critical problem - Alice and Bob think they're secure, but they have different keys!

---

## Scenario III: RSA Authentication

### RSA Key Generation Function

```python
def rsa_keygen(bits=512):
```
**Explanation**: Function to generate RSA key pairs. Default is 512-bit primes (1024-bit modulus).

```python
    P = random_prime(2**bits - 1, lbound=2**(bits-1))
```
**Explanation**: Generate first large prime `P` with exactly `bits` bits (512 bits).

```python
    Q = random_prime(2**bits - 1, lbound=2**(bits-1))
    while P == Q:
        Q = random_prime(2**bits - 1, lbound=2**(bits-1))
```
**Explanation**: 
- Generate second prime `Q` (also 512 bits)
- Ensure `Q ≠ P` (extremely unlikely, but we check anyway)

```python
    N = P * Q
```
**Explanation**: 
- Calculate RSA modulus: `N = P * Q`
- This is about 1024 bits (512 + 512)
- `N` is the public modulus

```python
    phi = (P - 1) * (Q - 1)
```
**Explanation**: 
- Calculate Euler's totient function: `φ(N) = (P-1)(Q-1)`
- This counts how many numbers less than N are coprime to N
- Used to calculate the private exponent

```python
    e = 65537
```
**Explanation**: 
- Set public exponent to 65537 (standard choice)
- In binary: 10000000000000001 (only two 1-bits = fast computation)
- Commonly used value (2^16 + 1)

```python
    while gcd(e, phi) != 1:
        e = next_prime(e)
```
**Explanation**: 
- Ensure `gcd(e, φ) = 1` (e and φ must be coprime)
- If not, find the next prime
- Usually 65537 works fine

```python
    d = inverse_mod(e, phi)
```
**Explanation**: 
- Calculate private exponent: `d = e^(-1) mod φ`
- This means: `e * d ≡ 1 (mod φ)`
- `d` is the **secret** decryption/signing exponent

```python
    dP = d % (P - 1)
```
**Explanation**: Precompute `dP = d mod (P-1)` for CRT optimization.

```python
    dQ = d % (Q - 1)
```
**Explanation**: Precompute `dQ = d mod (Q-1)` for CRT optimization.

```python
    qInv = inverse_mod(Q, P)
```
**Explanation**: 
- Precompute `qInv = Q^(-1) mod P`
- This is used to combine results in CRT

```python
    public_key = (N, e)
    private_key = (d, P, Q, dP, dQ, qInv)
    return public_key, private_key
```
**Explanation**: 
- Return tuple of public key (can be shared)
- Return tuple of private key (must be kept secret)

---

### RSA Signing with CRT

```python
def rsa_sign_crt(message, private_key):
```
**Explanation**: Function to sign a message using the **Chinese Remainder Theorem** for speed.

```python
    m = Integer(message)
```
**Explanation**: Convert message to SageMath Integer type (handles large numbers).

```python
    d, P, Q, dP, dQ, qInv = private_key
```
**Explanation**: Unpack all components of the private key.

```python
    m1 = power_mod(m, dP, P)
```
**Explanation**: 
- Compute `m1 = m^dP mod P`
- This is the signature **modulo P** (smaller calculation!)
- Uses fast modular exponentiation

```python
    m2 = power_mod(m, dQ, Q)
```
**Explanation**: 
- Compute `m2 = m^dQ mod Q`
- This is the signature **modulo Q** (smaller calculation!)

```python
    h = (qInv * (m1 - m2)) % P
```
**Explanation**: 
- CRT combination step
- Calculate adjustment factor `h`

```python
    s = m2 + h * Q
```
**Explanation**: 
- Final CRT reconstruction: `s = m2 + h * Q`
- Mathematical fact: `s ≡ m^d (mod N)`
- This is the **signature**
- **Advantage**: We did two small exponentiations instead of one huge one!

```python
    return s
```
**Explanation**: Return the signature.

---

### RSA Verification

```python
def rsa_verify(message, signature, public_key):
```
**Explanation**: Function to verify an RSA signature.

```python
    N, e = public_key
```
**Explanation**: Unpack the public key (N and e are public knowledge).

```python
    m = Integer(message)
    s = Integer(signature)
```
**Explanation**: Convert to SageMath integers.

```python
    m_prime = power_mod(s, e, N)
```
**Explanation**: 
- Compute `m' = s^e mod N`
- If signature is valid: `(m^d)^e = m^(d*e) = m (mod N)`
- Because `d*e ≡ 1 (mod φ)`

```python
    return m_prime == m
```
**Explanation**: 
- Check if recovered message equals original
- Returns `True` if signature is valid
- Returns `False` if signature is forged/invalid

---

### Using RSA with DH

```python
pub_A, priv_A = rsa_keygen(bits=512)
pub_B, priv_B = rsa_keygen(bits=512)
```
**Explanation**: Alice and Bob each generate their own RSA key pairs.

```python
sig_A = rsa_sign_crt(S_A, priv_A)
```
**Explanation**: 
- Alice signs her DH public signal `S_A` using her RSA private key
- This proves: "I (Alice) generated S_A"

```python
sig_B = rsa_sign_crt(S_B, priv_B)
```
**Explanation**: Bob signs his DH public signal `S_B`.

```python
is_valid_B = rsa_verify(S_B, sig_B, pub_B)
```
**Explanation**: 
- Alice verifies Bob's signature using Bob's **public key**
- If valid, Alice knows `S_B` really came from Bob

```python
if is_valid_B:
    print("Alice verified Bob's signature successfully.")
    K_A_auth = S_B**x_A
```
**Explanation**: 
- Only if signature verifies, Alice computes the shared key
- Now she knows she's really sharing a key with Bob, not an attacker!

```python
is_valid_A = rsa_verify(S_A, sig_A, pub_A)
if is_valid_A:
    print("Bob verified Alice's signature successfully.")
    K_B_auth = S_A**x_B
```
**Explanation**: Bob does the same verification for Alice's signature.

---

## Scenario IV: Defeating MITM

```python
x_C = randint(2, p-2)
S_C = g**x_C
```
**Explanation**: Charlie generates his fake signal.

```python
fake_sig_random = randint(0, pub_B[0]-1)
```
**Explanation**: 
- Charlie tries to create a fake signature by just picking a random number
- This won't work!

```python
is_valid_attack_A = rsa_verify(S_C, fake_sig_random, pub_B)
```
**Explanation**: 
- Alice tries to verify the signature using Bob's public key
- `(fake_sig)^e mod N` will NOT equal `S_C`
- Verification fails!

```python
if not is_valid_attack_A:
    print("Alice REJECTED the fake signature (Random). Attack FAILED.")
```
**Explanation**: Alice detects the attack and refuses the connection.

```python
pub_C, priv_C = rsa_keygen(bits=512)
fake_sig_charlie = rsa_sign_crt(S_C, priv_C)
```
**Explanation**: 
- Charlie tries another approach: sign with his own private key
- The signature is mathematically valid for Charlie's key pair

```python
is_valid_attack_B = rsa_verify(S_C, fake_sig_charlie, pub_B)
```
**Explanation**: 
- Alice verifies using **Bob's** public key
- But the signature was created with **Charlie's** private key
- They don't match! Verification fails!

```python
if not is_valid_attack_A and not is_valid_attack_B:
    print("CONCLUSION: The Man-in-the-Middle attack is successfully prevented by RSA authentication.")
```
**Explanation**: 
- Both attack attempts fail
- RSA signatures successfully prevent MITM attacks!
- **Key insight**: Charlie cannot create a valid signature for Bob's public key without Bob's private key

---

## Key Security Principles

1. **Diffie-Hellman Security**: Based on discrete logarithm problem (hard to find x from g^x)
2. **RSA Security**: Based on factoring problem (hard to find P and Q from N = P*Q)
3. **Authentication**: Signatures prove identity, preventing impersonation
4. **CRT Optimization**: ~4x faster signing by using Chinese Remainder Theorem
