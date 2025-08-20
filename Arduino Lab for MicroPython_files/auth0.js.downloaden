const APP_URL = "https://lab-micropython.arduino.cc"
const AUTH0_DOMAIN = "login.arduino.cc"
const AUTH0_CLIENT_ID = "Nsf3AfKOTw6Au9AGi8ALecA3aN3pVBcH"

class Auth {
  #auth0Client;

  async configureClient(){
    this.#auth0Client = await auth0.createAuth0Client({
      domain: AUTH0_DOMAIN,
      clientId: AUTH0_CLIENT_ID
    });
  };

  async isAuthenticated(){
    return await this.#auth0Client.isAuthenticated();
  };

  async handleRedirectCallback(){
    await this.#auth0Client.handleRedirectCallback();
  };

  async login(){
    await this.#auth0Client.loginWithRedirect({
      authorizationParams: {
        redirect_uri: window.location.origin
      }
    });
  };

  async logout(){
    await this.#auth0Client.logout({
      returnTo: APP_URL
    });
  };
}

window.onload = async () => {
  
  let auth = new Auth();
  window._logout = async() => {auth.logout()}; 
  
  await auth.configureClient();

  const isAuthenticated = await auth.isAuthenticated();  

  if(!isAuthenticated){

    const query = window.location.search;
    if (query.includes("code=") && query.includes("state=")) {
        // Process the login state
        try{
            await auth.handleRedirectCallback();
        } catch(err){
            console.error("Error during redirect: ", error);
        }

        window.location = APP_URL   
            
    } else {
        //Require Login
        auth.login();
    }
    
  }
}

