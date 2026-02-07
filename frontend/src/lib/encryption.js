import nacl from 'tweetnacl';
import { encodeBase64, decodeBase64, decodeUTF8 } from 'tweetnacl-util';

const AUTHORITY_PUBLIC_KEY = import.meta.env.VITE_AUTHORITY_PUBLIC_KEY;

export function encryptWithNaCl(plaintext) {
  if (!AUTHORITY_PUBLIC_KEY) {
    throw new Error('Authority public key not configured');
  }
  
  // Generate random symmetric key (256-bit)
  const symmetricKey = nacl.randomBytes(32);
  const nonce = nacl.randomBytes(24);
  
  // Encrypt with secretbox (XSalsa20-Poly1305)
  const messageBytes = decodeUTF8(plaintext);
  const ciphertext = nacl.secretbox(messageBytes, nonce, symmetricKey);
  
  // Generate ephemeral keypair to encrypt symmetric key
  const ephemeralKeypair = nacl.box.keyPair();
  const authorityPubKey = decodeBase64(AUTHORITY_PUBLIC_KEY);
  
  // Encrypt symmetric key with authority's public key
  const encryptedKey = nacl.box(
    symmetricKey,
    nonce,
    authorityPubKey,
    ephemeralKeypair.secretKey
  );
  
  return {
    ciphertext: encodeBase64(ciphertext),
    encryptedKey: encodeBase64(encryptedKey),
    ephemeralPublicKey: encodeBase64(ephemeralKeypair.publicKey),
    nonce: encodeBase64(nonce)
  };
}

// Encrypt a file (returns base64)
export async function encryptFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const arrayBuffer = reader.result;
        const bytes = new Uint8Array(arrayBuffer);
        
        // Generate keys
        const symmetricKey = nacl.randomBytes(32);
        const nonce = nacl.randomBytes(24);
        
        // Encrypt file data
        const ciphertext = nacl.secretbox(bytes, nonce, symmetricKey);
        
        // Encrypt symmetric key with authority's public key
        const ephemeralKeypair = nacl.box.keyPair();
        const authorityPubKey = decodeBase64(AUTHORITY_PUBLIC_KEY);
        
        const encryptedKey = nacl.box(
          symmetricKey,
          nonce,
          authorityPubKey,
          ephemeralKeypair.secretKey
        );
        
        resolve({
          filename: file.name,
          type: file.type,
          size: file.size,
          ciphertext: encodeBase64(ciphertext),
          encryptedKey: encodeBase64(encryptedKey),
          ephemeralPublicKey: encodeBase64(ephemeralKeypair.publicKey),
          nonce: encodeBase64(nonce)
        });
      } catch (err) {
        reject(err);
      }
    };
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });
}


