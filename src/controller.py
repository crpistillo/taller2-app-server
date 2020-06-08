import json
import logging
from typing import Optional
from flask import request
from flask_httpauth import HTTPTokenAuth
from constants import messages
from src.services.auth_server import AuthServer
from src.model.photo import Photo
from src.services.exceptions.invalid_credentials_error import InvalidCredentialsError
from src.services.exceptions.user_already_registered_error import UserAlreadyRegisteredError
from src.services.exceptions.invalid_login_token_error import InvalidLoginTokenError
from src.services.exceptions.unexistent_user_error import UnexistentUserError
from src.services.exceptions.invalid_register_field_error import InvalidRegisterFieldError


auth = HTTPTokenAuth(scheme='Bearer')

LOGIN_MANDATORY_FIELDS = {"email", "password"}
API_KEY_CREATE_MANDATORY_FIELDS = {"alias", "secret"}
RECOVER_PASSWORD_MANDATORY_FIELDS = {"email"}
NEW_PASSWORD_MANDATORY_FIELDS = {"email", "new_password", "token"}
USERS_REGISTER_MANDATORY_FIELDS = {"email", "password", "phone_number", "fullname"}

class Controller:
    logger = logging.getLogger(__name__)
    def __init__(self, auth_server: AuthServer):
        """
        Here the init should receive all the parameters needed to know how to answer all the queries
        """
        self.auth_server = auth_server
        @auth.verify_token
        def verify_token(token) -> Optional[str]:
            """
            Verifies a token

            :param token: the token to verify
            :return: the corresponding user
            """
            return auth_server.get_logged_email(token)

    def api_health(self):
        """
        A dumb api health

        :return: a tuple with the text and the status to return
        """
        return messages.SUCCESS_JSON, 200

    def users_register(self):
        """
        Handles the user registration
        :return: a json with a success message on success or an error in another case
        """
        content = request.form
        if not USERS_REGISTER_MANDATORY_FIELDS.issubset(content.keys()):
            self.logger.debug(messages.MISSING_FIELDS_ERROR)
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR, 400
        photo = Photo()
        if 'photo' in request.files:
            photo = Photo.from_bytes(request.files['photo'].stream)
        try:
            self.auth_server.user_register(email=content["email"], fullname=content["fullname"],
                                           phone_number=content["phone_number"], photo=photo,
                                           plain_password=content["password"])
        except UserAlreadyRegisteredError:
            self.logger.debug(messages.USER_ALREADY_REGISTERED_MESSAGE)
            return messages.ERROR_JSON % messages.USER_ALREADY_REGISTERED_MESSAGE, 400
        except InvalidRegisterFieldError as e:
            self.logger.debug(str(e))
            return messages.ERROR_JSON % str(e), 400
        return messages.SUCCESS_JSON, 200

    def users_login(self):
        """
        Handles the user login
        :return: a json with the login_token on success or an error in another case
        """
        try:
            assert request.is_json
        except AssertionError:
            self.logger.debug(messages.REQUEST_IS_NOT_JSON)
            return messages.ERROR_JSON % messages.REQUEST_IS_NOT_JSON, 400
        content = request.get_json()
        if not LOGIN_MANDATORY_FIELDS.issubset(content.keys()):
            self.logger.debug(messages.MISSING_FIELDS_ERROR)
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR, 400
        try:
            login_token = self.auth_server.user_login(email=content["email"], plain_password=content["password"])
        except InvalidCredentialsError:
            self.logger.debug(messages.WRONG_CREDENTIALS_MESSAGE)
            return messages.ERROR_JSON % messages.WRONG_CREDENTIALS_MESSAGE, 403
        return json.dumps({"login_token": login_token})

    def users_profile_query(self):
        """
        Handles the user recovering
        :return: a json with the data of the requested user on success or an error in another case
        """
        email_query = request.args.get('email')
        if not email_query:
            self.logger.debug(messages.MISSING_FIELDS_ERROR)
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR, 400
        try:
            user_data = self.auth_server.profile_query(email_query)
        except UnexistentUserError:
            self.logger.debug(messages.USER_NOT_FOUND_MESSAGE % email_query)
            return messages.ERROR_JSON % (messages.USER_NOT_FOUND_MESSAGE % email_query), 404
        return json.dumps(user_data)
