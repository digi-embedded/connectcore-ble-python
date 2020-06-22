# AES modules
from Crypto.Cipher import AES
from Crypto.Util import Counter

# SRP modules
import srp
from srp_phase import SrpPhase
from srp_phase import SrpError

# XBee modules
from digi.xbee.packets.base import UnknownXBeePacket

# ConnectCore BLE modules
from exception import NotAuthenticatedException

# Standard modules
import utils
import os

API_USERNAME = 'apiservice'

class BLESecurityManager:
    salt = None
    verification_key = None

    encryptor = None
    decryptor = None

    encrypt = False

    @staticmethod
    def new_cipher(session_key, nonce):
        counter = Counter.new(nbits=32, prefix=nonce, initial_value=1)
        cipher = AES.new(key=session_key, mode=AES.MODE_CTR, counter=counter)
        return cipher

    @classmethod
    def encrypt_data(cls, data):
        """
        Encrypts the given data with the stored encrypt cipher if the encrypt flag is set to True.

        Args:
            data (Bytearray): Plain data to be encrypted.

        Returns:
            Bytearray - Encrypted data or plain data if the encrypt flag is set to False.
        """
        if cls.encrypt:
            return bytearray(cls.encryptor.encrypt(bytes(data)))
        raise NotAuthenticatedException()

    @classmethod
    def decrypt_data(cls, data):
        """
        Decrypts the given data with the stored decrypt cipher if the encrypt flag is set to True.

        Args:
            data (Bytearray): Encrypted data to be decrypted.

        Returns:
            Bytearray - Decrypted data or encrypted data if the encrypt flag is set to False.
        """
        if cls.encrypt:
            return bytearray(cls.decryptor.decrypt(bytes(data)))
        raise NotAuthenticatedException()

    @classmethod
    def generate_salted_verification_key(cls, api_password):
        cls.salt, cls.verification_key = srp.create_salted_verification_key(API_USERNAME, api_password,
                                                                            hash_alg=srp.SHA256,
                                                                            ng_type=srp.NG_1024, salt_len=4)

    @classmethod
    def process_srp_request(cls, frame_data):
        """
        Processes the SRP request contained in the given data.

        Args:
            frame_data (bytes): Data containing the SRP request.
        """

        if frame_data[4] == SrpPhase.PHASE_1.code:
            payload = SrpPhase.PHASE_2.code.to_bytes(1, byteorder='big')
            client_ephemeral_A = bytes.fromhex(utils.hex_to_string(frame_data[5:133]))

            cls.verifier = srp.Verifier(API_USERNAME, cls.salt, cls.verification_key, client_ephemeral_A,
                                        hash_alg=srp.SHA256, ng_type=srp.NG_1024)
            _, server_ephemeral_B = cls.verifier.get_challenge()

            if server_ephemeral_B is None:
                # Add error code to payload.
                payload = SrpError.B_OFFERING_ERROR.code
            else:
                payload += cls.salt
                payload += server_ephemeral_B

            return UnknownXBeePacket(0xAC, bytearray(payload)).output()
        elif frame_data[4] == SrpPhase.PHASE_3.code:
            payload = SrpPhase.PHASE_4.code.to_bytes(1, byteorder='big')
            client_proof_M1 = bytes.fromhex(utils.hex_to_string(frame_data[5:37]))

            server_proof_M2 = cls.verifier.verify_session(client_proof_M1)
            key = None

            if server_proof_M2 is None or not cls.verifier.authenticated():
                # Add error code to payload.
                payload = SrpError.BAD_PROOF_OF_KEY.code.to_bytes(1, byteorder='big')
            else:
                # Generate random nonces.
                tx_nonce = os.urandom(12)
                rx_nonce = os.urandom(12)

                payload += server_proof_M2
                payload += tx_nonce
                payload += rx_nonce

                key = cls.verifier.get_session_key()

                # Create encryptor and decryptor.
                cls.encryptor = cls.new_cipher(key, rx_nonce)
                cls.decryptor = cls.new_cipher(key, tx_nonce)

            if key is not None:
                cls.encrypt = True

            return UnknownXBeePacket(0xAC, bytearray(payload)).output()
