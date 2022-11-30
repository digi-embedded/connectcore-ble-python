# Copyright 2022, Digi International Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import os

from enum import Enum, unique

import srp

from Crypto.Cipher import AES
from Crypto.Util import Counter
from digi.ccble import utils
from digi.ccble.exceptions import NotAuthenticatedException
from digi.xbee.packets.base import UnknownXBeePacket

@unique
class SrpPhase(Enum):
    """
    Enumeration class listing all the SRP phases.
    """
    PHASE_1 = (0x01, "Phase 1: Client presents A value")
    PHASE_2 = (0x02, "Phase 2: Server presents B and salt")
    PHASE_3 = (0x03, "Phase 3: Client presents M1 session key validation value")
    PHASE_4 = (0x04, "Phase 4: Server presents M2 session key validation value and two 12-byte nonces")
    UNKNOWN = (0xFF, "Unknown")

    def __init__(self, code, description):
        """
        Class constructor. Instantiates a new `SrpPhase` entry with the provided parameters.

        Args:
            code (Integer): SRP phase code.
            description (String): SRP phase description.
        """
        self.__code = code
        self.__description = description

    @property
    def code(self):
        """
        Returns the SRP phase code.

        Returns:
            Integer: SRP phase code.
        """
        return self.__code

    @property
    def description(self):
        """
        Returns the SRP phase description.

        Returns:
            String: SRP phase description.
        """
        return self.__description

    @classmethod
    def get(cls, code):
        """
        Returns the SRP phase corresponding to the given code.

        Args:
            code (Integer): SRP phase code.

        Returns:
            SrpPhase: SRP phase corresponding to the given code.
        """
        for srp_phase in cls:
            if code == srp_phase.code:
                return srp_phase
        return SrpPhase.UNKNOWN


@unique
class SrpError(Enum):
    """
    Enumeration class listing all the SRP errors.
    """
    B_OFFERING_ERROR = (0x80, "Unable to offer B (cryptographic error with content, usually due to A mod N == 0")
    INCORRECT_LENGTH = (0x81, "Incorrect payload length")
    BAD_PROOF_OF_KEY = (0x82, "Bad proof of key")
    ALLOCATION_ERROR = (0x83, "Resource allocation error")
    WRONG_STEP_ERROR = (0x84, "Request contained a step not in the correct sequence")

    def __init__(self, code, description):
        """
        Class constructor. Instantiates a new `SrpError` entry with the provided parameters.

        Args:
            code (Integer): SRP error code.
            description (String): SRP error description.
        """
        self.__code = code
        self.__description = description

    @property
    def code(self):
        """
        Returns the SRP error code.

        Returns:
            Integer: SRP error code.
        """
        return self.__code

    @property
    def description(self):
        """
        Returns the SRP error description.

        Returns:
            String: SRP error description.
        """
        return self.__description

    @classmethod
    def get(cls, code):
        """
        Returns the SRP error corresponding to the given code.

        Args:
            code (Integer): SRP error code.

        Returns:
            SrpError: SRP error corresponding to the given code, `None` if not found.
        """
        for srp_error in cls:
            if code == srp_error.code:
                return srp_error
        return None


SrpPhase.__doc__ += utils.doc_enum(SrpPhase)
SrpError.__doc__ += utils.doc_enum(SrpError)


class SRPSecurityManager:
    """
    Helper class used to handle SRP authentication protocol with a remote device in order to encrypt
    and decrypt data.
    """

    # Constants.
    _DEFAULT_USERNAME = 'apiservice'

    def __init__(self):
        """
        Class constructor. Instantiates a new `SRPSecurityManager` object.
        """
        # Initialize variables.
        self._salt = None
        self._verification_key = None
        self._verifier = None
        self._encryptor = None
        self._decryptor = None
        self._authenticated = False

    def is_authenticated(self):
        """
        Returns whether the session is authenticated or not.

        Returns:
            Boolean: `True` if the session is authenticated, `False` otherwise.
        """
        return self._authenticated

    def deauthenticate(self):
        """
        Deauthenticate the security manager.
        """
        self._authenticated = False

    @staticmethod
    def new_cipher(session_key, nonce):
        """
        Creates a new AES cipher with the given session key and nonce.

        Args:
            session_key (Bytearray): Session key.
            nonce (Bytearray): Nonce.

        Returns:
            :class:`.AES`: AES cipher.
        """
        counter = Counter.new(nbits=32, prefix=nonce, initial_value=1)
        cipher = AES.new(key=session_key, mode=AES.MODE_CTR, counter=counter)
        return cipher

    def encrypt_data(self, data):
        """
        Encrypts the given data with the stored encrypt cipher.

        Args:
            data (Bytearray): Data to be encrypt.

        Returns:
            Bytearray: Encrypted data.

        Raises:
            NotAuthenticatedException: If the user is not authenticated.
        """
        # Sanity checks.
        if not self._authenticated:
            raise NotAuthenticatedException()

        return bytearray(self._encryptor.encrypt(bytes(data)))

    def decrypt_data(self, data):
        """
        Decrypts the given data with the stored decrypt cipher.

        Args:
            data (Bytearray): Data to be decrypt.

        Returns:
            Bytearray: Decrypted data.

        Raises:
            NotAuthenticatedException: If the user is not authenticated.
        """
        # Sanity checks.
        if not self._authenticated:
            raise NotAuthenticatedException()

        return bytearray(self._decryptor.decrypt(bytes(data)))

    def generate_salted_verification_key(self, password):
        """
        Generates and stores a salted verification key from the given password.

        Args:
            password (String): Password to use to generate the salted verification key.
        """
        self._salt, self._verification_key = srp.create_salted_verification_key(self._DEFAULT_USERNAME,
                                                                                password,
                                                                                hash_alg=srp.SHA256,
                                                                                ng_type=srp.NG_1024,
                                                                                salt_len=4)

    def process_srp_request(self, frame_data):
        """
        Processes the SRP request contained in the given data and returns an XBee packet with the
        answer.

        Args:
            frame_data (bytes): Data containing the SRP request.

        Returns:
            :class:`.XBeeAPIPacket`: XBee packet containing the SRP answer, `None` if the request is
                                     not an SRP request.
        """
        srp_phase = SrpPhase.get(frame_data[4])
        if srp_phase == SrpPhase.PHASE_1:
            # Phase 1: Client presents 'A' value, we have to present 'B' value and salt.
            # --------------------------------------------------------------------------
            # Initialize payload.
            payload = SrpPhase.PHASE_2.code.to_bytes(1, byteorder='big')
            # Extract client 'ephemeral a' from the given data.
            client_ephemeral_a = bytes.fromhex(utils.hex_to_string(frame_data[5:133]))
            # Generate SRP verifier with the stored salted key and the ephemeral_a.
            self._verifier = srp.Verifier(self._DEFAULT_USERNAME,
                                          self._salt,
                                          self._verification_key,
                                          client_ephemeral_a,
                                          hash_alg=srp.SHA256,
                                          ng_type=srp.NG_1024)
            # Calculate server 'ephemeral b'.
            _, server_ephemeral_b = self._verifier.get_challenge()
            # Check for error.
            if server_ephemeral_b is None:
                # Add error code to payload.
                payload = SrpError.B_OFFERING_ERROR.code
            else:
                # Add server 'ephemeral b' and 'salt' to payload.
                payload += self._salt
                payload += server_ephemeral_b
            # Generate and return an XBee packet with the payload.
            return UnknownXBeePacket(0xAC, bytearray(payload)).output()
        if srp_phase == SrpPhase.PHASE_3:
            # Phase 3: Client presents 'M1 session key validation value,' we have to present
            # 'M2 session key validation value' and two 12-byte 'nonces'.
            # ------------------------------------------------------------------------------
            # Initialize payload.
            payload = SrpPhase.PHASE_4.code.to_bytes(1, byteorder='big')
            # Extract 'client proof m1' from the given data.
            client_proof_m1 = bytes.fromhex(utils.hex_to_string(frame_data[5:37]))
            # Calculate 'server proof m2'.
            server_proof_m2 = self._verifier.verify_session(client_proof_m1)
            # Initialize key.
            key = None
            # Check for error.
            if server_proof_m2 is None or not self._verifier.authenticated():
                # Add error code to payload.
                payload = SrpError.BAD_PROOF_OF_KEY.code.to_bytes(1, byteorder='big')
            else:
                # Generate two 12-byte random 'nonces'.
                tx_nonce = os.urandom(12)
                rx_nonce = os.urandom(12)
                # Fill payload.
                payload += server_proof_m2
                payload += tx_nonce
                payload += rx_nonce
                # Extract session key.
                key = self._verifier.get_session_key()
                # Create encryptor and decryptor using the session key and generated 'nonces'.
                self._encryptor = self.new_cipher(key, rx_nonce)
                self._decryptor = self.new_cipher(key, tx_nonce)
            # Check if key generation succeed.
            if key is not None:
                self._authenticated = True
            # Generate and return an XBee packet with the payload.
            return UnknownXBeePacket(0xAC, bytearray(payload)).output()

        # Invalid SRP phase or not SRP request packet.
        return None
