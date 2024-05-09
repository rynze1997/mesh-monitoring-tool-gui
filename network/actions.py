# Import other network services as needed
from .authenticate import Authenticator

class AuthHandler(Authenticator):
    def __init__(self):
        super().__init__()
    def execute_login(self, app_data, success_callback, failure_callback):
        # Authentication logic
        result = self.login(server=app_data['server'], username=app_data['username'], password=app_data['password'])
        
        if result:
            success_callback()
        else:
            # Update GUI to reflect failed authentication
            failure_callback()
            
    def getSiteNames(self):
        site_names = self.site_names()
        return site_names
    
    def getSiteData(self, siteName):
        site_data = self.site_data(siteName)
        return site_data
    
    def getSiteIndices(self, siteName):
        return self.site_indices(siteName)
    
    def getSiteUsername(self):
        return self.site_username()
