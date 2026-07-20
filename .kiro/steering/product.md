# Product: QRIS Quantum Threat Demo

An interactive educational demo simulating a **Man-in-the-Middle + Quantum Forge** attack against an RSA-based Dynamic QRIS payment system. Built for **Post-Quantum Cryptography (PQC) awareness** at Telkom/SBDP.

## Purpose

Demonstrates why RSA-based QRIS is vulnerable to quantum computers by walking through a live attack scenario:
1. Bank generates RSA keypair and signs a QRIS payment code
2. Attacker intercepts the QRIS, runs a simulated Shor's algorithm to crack the private key, and forges a fraudulent QRIS
3. M-Banking app verifies the forged QRIS as valid (RSA signature passes), and the customer unknowingly pays the attacker

## Entities / Roles

- **Kasir (Merchant)**: Generates QRIS codes signed with the bank's RSA key
- **Attacker**: Intercepts packets, simulates quantum factorization (Shor's), forges QRIS
- **M-Banking (Customer)**: Scans and pays — unaware the QRIS has been tampered with

## Key Demo Points

- RSA-52bit modulus is used intentionally (insecure by design) to allow real factorization in ~2–4 seconds, dramatizing the quantum threat
- Pollard's Rho (classical) runs in parallel for comparison
- The forged QRIS passes RSA signature verification, illustrating the core PQC problem
- Target audience: security awareness, not production use — this is a demo/educational tool only

## Language

UI and logs are in **Bahasa Indonesia**. Code comments and docstrings are also in Indonesian.
