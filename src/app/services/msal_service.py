"""Microsoft Authentication Library (MSAL) service for Entra ID authentication"""
import msal
from flask import current_app, session, url_for
from typing import Optional, Dict


class MSALService:
    """Service for handling Entra ID authentication using MSAL"""

    @staticmethod
    def _get_msal_app():
        """Get or create MSAL confidential client application"""
        authority = f"{current_app.config['AUTHORITY']}{current_app.config['AZURE_TENANT_ID']}"

        return msal.ConfidentialClientApplication(
            current_app.config['AZURE_CLIENT_ID'],
            authority=authority,
            client_credential=current_app.config['AZURE_CLIENT_SECRET']
        )

    @staticmethod
    def get_auth_url(state: str = None) -> str:
        """
        Generate the authorization URL for Entra ID login

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        msal_app = MSALService._get_msal_app()

        auth_url = msal_app.get_authorization_request_url(
            scopes=current_app.config['SCOPE'],
            state=state,
            redirect_uri=current_app.config['REDIRECT_URI']
        )

        return auth_url

    @staticmethod
    def acquire_token_by_auth_code(auth_code: str) -> Optional[Dict]:
        """
        Exchange authorization code for access token

        Args:
            auth_code: Authorization code received from callback

        Returns:
            Token response dictionary or None if failed
        """
        msal_app = MSALService._get_msal_app()

        result = msal_app.acquire_token_by_authorization_code(
            auth_code,
            scopes=current_app.config['SCOPE'],
            redirect_uri=current_app.config['REDIRECT_URI']
        )

        return result

    @staticmethod
    def get_token_from_cache() -> Optional[Dict]:
        """
        Try to get token from cache

        Returns:
            Token response or None if no valid token in cache
        """
        if 'user' not in session:
            return None

        msal_app = MSALService._get_msal_app()
        accounts = msal_app.get_accounts()

        if accounts:
            result = msal_app.acquire_token_silent(
                current_app.config['SCOPE'],
                account=accounts[0]
            )
            return result

        return None

    @staticmethod
    def remove_account():
        """Remove account from MSAL cache"""
        msal_app = MSALService._get_msal_app()
        accounts = msal_app.get_accounts()

        for account in accounts:
            msal_app.remove_account(account)

    @staticmethod
    def get_user_info(token: str) -> Optional[Dict]:
        """
        Get user information from Microsoft Graph API

        Args:
            token: Access token

        Returns:
            User info dictionary with email, name, etc.
        """
        import requests

        graph_endpoint = 'https://graph.microsoft.com/v1.0/me'

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.get(graph_endpoint, headers=headers)
            response.raise_for_status()
            user_data = response.json()

            return {
                'email': user_data.get('mail') or user_data.get('userPrincipalName'),
                'name': user_data.get('displayName'),
                'azure_oid': user_data.get('id'),
                'given_name': user_data.get('givenName'),
                'surname': user_data.get('surname')
            }
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error fetching user info from Graph API: {e}")
            return None
