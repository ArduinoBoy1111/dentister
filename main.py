import os
import webview
import urllib.parse


def get_url(relative_path):
    abs_path = os.path.abspath(relative_path)
    return f"file:///{urllib.parse.quote(abs_path.replace(os.sep, '/'))}"

def load_page(name):
    if name == "index":
        return get_url("assets/index.html")
    elif name == "patients":
        return get_url("assets/patients.html")
    elif name == "settings":
        return get_url("assets/settings.html")
    
    return get_url("assets/404.html")

class API:
    def navigate(self, page_name):
        url = load_page(page_name)
        window.load_url(url)
      
api = API()
window = webview.create_window("Dentister", load_page("index"), js_api=api)
webview.start()
