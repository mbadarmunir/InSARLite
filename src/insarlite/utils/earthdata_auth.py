"""
Unified EarthData authentication system using cookie jar method.
This module provides centralized authentication for all EarthData services
including ASF searches, orbit downloads, and data downloads.
"""

import os
import base64
import tkinter as tk
from tkinter import simpledialog
from urllib.request import (
    build_opener, install_opener, Request, urlopen,
    HTTPCookieProcessor, HTTPHandler, HTTPSHandler
)
from http.cookiejar import MozillaCookieJar
import requests
import asf_search as asf


class EarthDataAuth:
    """Unified EarthData authentication using cookie jar for persistent sessions."""
    
    def __init__(self):
        """Initialize the authentication system."""
        self.cookie_jar_path = os.path.join(os.path.expanduser('~'), ".earthdata_cookiejar.txt")
        self.cookie_jar = MozillaCookieJar()
        self.username = None
        self.password = None
        self._session = None
        
    def _check_cookie(self):
        """Check if existing cookie is still valid."""
        if not self.cookie_jar:
            return False
            
        file_check = 'https://urs.earthdata.nasa.gov/profile'
        opener = build_opener(
            HTTPCookieProcessor(self.cookie_jar),
            HTTPHandler(),
            HTTPSHandler()
        )
        install_opener(opener)
        request = Request(file_check)
        request.get_method = lambda: 'HEAD'
        
        try:
            response = urlopen(request, timeout=30)
            if response.getcode() in (200, 307):
                self.cookie_jar.save(self.cookie_jar_path)
                return True
        except Exception:
            return False
        return False
    
    def _prompt_credentials(self):
        """Prompt user for EarthData credentials using GUI dialog."""
        class LoginDialog(simpledialog.Dialog):
            def body(self, master):
                tk.Label(master, text="EarthData Username:").grid(row=0, sticky="e", padx=5, pady=5)
                tk.Label(master, text="EarthData Password:").grid(row=1, sticky="e", padx=5, pady=5)
                self.username_entry = tk.Entry(master, width=30)
                self.password_entry = tk.Entry(master, show="*", width=30)
                self.username_entry.grid(row=0, column=1, padx=5, pady=5)
                self.password_entry.grid(row=1, column=1, padx=5, pady=5)
                return self.username_entry

            def apply(self):
                self.result = (
                    self.username_entry.get(),
                    self.password_entry.get()
                )

        root = tk.Tk()
        root.withdraw()
        dialog = LoginDialog(root, title="EarthData Login Required")
        root.destroy()
        
        if dialog.result:
            username, password = dialog.result
            if username and password:
                return username, password
        
        raise Exception("EarthData credentials are required for this operation.")
    
    def _authenticate_with_credentials(self, username, password):
        """Authenticate using username/password and save cookies."""
        auth_cookie_url = (
            "https://urs.earthdata.nasa.gov/oauth/authorize"
            "?client_id=BO_n7nTIlMljdvU6kRRB3g"
            "&redirect_uri=https://auth.asf.alaska.edu/login"
            "&response_type=code&state="
        )
        
        user_pass = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
        opener = build_opener(
            HTTPCookieProcessor(self.cookie_jar), 
            HTTPHandler(), 
            HTTPSHandler()
        )
        request = Request(auth_cookie_url, headers={"Authorization": f"Basic {user_pass}"})
        
        try:
            opener.open(request)
            # Save the credentials for this session
            self.username = username
            self.password = password
            return True
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False
    
    def ensure_authenticated(self, force_new=False):
        """
        Ensure user is authenticated with EarthData.
        
        Args:
            force_new (bool): Force new authentication even if cookies exist
            
        Returns:
            bool: True if authenticated successfully
        """
        if not force_new and os.path.isfile(self.cookie_jar_path):
            try:
                self.cookie_jar.load(self.cookie_jar_path)
                if self._check_cookie():
                    print("✓ Using existing EarthData authentication")
                    return True
                else:
                    print("⚠ Existing authentication expired")
            except Exception:
                print("⚠ Could not validate existing authentication")
        
        print("🔐 EarthData authentication required...")
        
        # Need new authentication
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                username, password = self._prompt_credentials()
                
                if self._authenticate_with_credentials(username, password):
                    if self._check_cookie():
                        print("✓ EarthData authentication successful")
                        return True
                    
                print(f"❌ Authentication failed (attempt {attempt + 1}/{max_attempts})")
                
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise Exception(f"Authentication failed after {max_attempts} attempts: {e}")
                print(f"❌ Authentication error: {e}")
        
        return False
    
    def get_authenticated_session(self):
        """
        Get a requests session with EarthData authentication.
        
        Returns:
            requests.Session: Authenticated session ready for EarthData requests
        """
        if not self.ensure_authenticated():
            raise Exception("Could not establish EarthData authentication")
        
        if self._session is None:
            self._session = requests.Session()
            
            # Add cookies to the session
            if os.path.isfile(self.cookie_jar_path):
                self.cookie_jar.load(self.cookie_jar_path)
                for cookie in self.cookie_jar:
                    self._session.cookies.set(cookie.name, cookie.value, domain=cookie.domain)
            
            # Set authentication credentials as backup
            if self.username and self.password:
                self._session.auth = (self.username, self.password)
        
        return self._session
    
    def get_credentials(self):
        """
        Get EarthData credentials (username, password).
        
        Returns:
            tuple: (username, password) if available, (None, None) otherwise
        """
        if not self.ensure_authenticated():
            return None, None
        return self.username, self.password
    
    def setup_asf_authentication(self):
        """Setup ASF search authentication using stored credentials or cookies."""
        if not self.ensure_authenticated():
            raise Exception("Could not establish EarthData authentication for ASF")
        
        try:
            # Configure ASF search with credentials
            asf.constants.CMR_TIMEOUT = 30
            # Set up session with authentication
            session = self.get_authenticated_session()
            
            # If we reach here, authentication is available (either credentials or cookies)
            # ASF search will use the session cookies automatically
            print("✓ ASF search authentication configured")
            return True
                
        except Exception as e:
            print(f"⚠ ASF authentication setup failed: {e}")
            return False
    
    def clear_authentication(self):
        """Clear stored authentication data."""
        try:
            if os.path.isfile(self.cookie_jar_path):
                os.remove(self.cookie_jar_path)
            self.cookie_jar.clear()
            self.username = None
            self.password = None
            if self._session:
                self._session.close()
                self._session = None
            print("✓ Authentication data cleared")
        except Exception as e:
            print(f"⚠ Error clearing authentication: {e}")


# Global instance for use across the application
earthdata_auth = EarthDataAuth()


def ensure_earthdata_auth(force_new=False):
    """
    Convenience function to ensure EarthData authentication.
    
    Args:
        force_new (bool): Force new authentication
        
    Returns:
        bool: True if authenticated
    """
    return earthdata_auth.ensure_authenticated(force_new)


def get_earthdata_session():
    """
    Convenience function to get authenticated requests session.
    
    Returns:
        requests.Session: Authenticated session
    """
    return earthdata_auth.get_authenticated_session()


def get_earthdata_credentials():
    """
    Convenience function to get EarthData credentials.
    
    Returns:
        tuple: (username, password)
    """
    return earthdata_auth.get_credentials()


def setup_asf_auth():
    """
    Convenience function to setup ASF authentication.
    
    Returns:
        bool: True if successful
    """
    return earthdata_auth.setup_asf_authentication()