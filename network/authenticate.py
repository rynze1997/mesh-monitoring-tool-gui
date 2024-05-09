from .parse.plejdParse import plejd

class Authenticator:
    
    def __init__(self):
        self.p = None
    
    def login(self, server, username, password):
        # Use input data to login
        if server == "STAGE":
            self.p = plejd(server=plejd.STAGE)
        elif server == "PROD":
            self.p = plejd(server=plejd.PRODUCTION)
        elif server == "DEV":
            self.p = plejd(server=plejd.DEV)
        elif server == "EDGE":
            self.p = plejd(server=plejd.EDGE)
        # Login
        login_res = self.p.login(username, password)
        self.p.getSites()
        site_names = list(self.p.siteIDs.keys())
        print(site_names)

        if login_res == 200:
            print(f"Logging in to {server} as {username}")
            return True
        else:
            print("Could not log in.")
            return False
        
    def site_names(self):
        self.p.getSites()
        site_names = list(self.p.siteIDs.keys())
        return site_names
    
    def site_data(self, siteName):
        self.p.getKey(siteName)
        return self.p.auth
    
    def site_indices(self, siteName):
        return self.p.getSiteIndicesForSite(siteName)
    
    def site_username(self):
        return self.p.username