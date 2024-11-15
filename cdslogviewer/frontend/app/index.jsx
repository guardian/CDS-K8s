import React from "react";
import { render } from "react-dom";
import { BrowserRouter, Navigate, Routes, Route } from "react-router-dom";
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  IconButton,
} from "@material-ui/core";
import axios from "axios";
import MainWindow from "./MainWindow";
import {
  AppSwitcher,
  Header,
  OAuthContextProvider,
  SystemNotification,
  UserContextProvider,
  verifyExistingLogin,
  handleUnauthorized,
} from "@guardian/pluto-headers";
import { Brightness4, Brightness7 } from "@material-ui/icons";
import createCustomisedTheme from "./theming";
import LogByJobName from "./LogByJobName";

const darkTheme = createCustomisedTheme({
  typography: {
    fontFamily: [
      "sans-serif",
      '"Helvetica Neue"',
      "Helvetica",
      "Arial",
      "sans-serif",
    ].join(","),
    fontWeight: 400,
  },
  palette: {
    type: "dark",
    logviewer: {
      main: "#00a000",
      background: "#000000e0",
    },
  },
});

const lightTheme = createCustomisedTheme({
  typography: {
    fontFamily: [
      "sans-serif",
      '"Helvetica Neue"',
      "Helvetica",
      "Arial",
      "sans-serif",
    ].join(","),
    fontWeight: 400,
  },
  palette: {
    type: "light",
    logviewer: {
      main: "#008000",
      background: "#00000020",
    },
  },
});

axios.interceptors.request.use(function (config) {
  const token = window.localStorage.getItem("pluto:access-token");
  if (token) config.headers.Authorization = `Bearer ${token}`;

  // this is set in the index.scala.html template file and gives us the value of deployment-root from the server config
  // Only apply deployment root when url begins with /api
  if (config.url.startsWith("/api")) {
    config.baseURL = deploymentRootPath;
  }

  return config;
});

class App extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      isDark: true,
      loading: true,
      isLoggedIn: false,
      tokenExpired: false,
      plutoConfig: {},
      userProfile: undefined,
    };

    this.handleUnauthorizedFailed = this.handleUnauthorizedFailed.bind(this);
    this.onLoginValid = this.onLoginValid.bind(this);
    this.oAuthConfigLoaded = this.oAuthConfigLoaded.bind(this);

    axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        handleUnauthorized(
          this.state.plutoConfig,
          error,
          this.handleUnauthorizedFailed
        );

        return Promise.reject(error);
      }
    );
  }

  handleUnauthorizedFailed() {
    this.setState({
      isLoggedIn: false,
      tokenExpired: true,
    });
  }

  async onLoginValid(valid, loginData) {
    // Fetch the OAuth config.
    try {
      const response = await fetch("/meta/oauth/config.json");
      if (response.status === 200) {
        const data = await response.json();
        this.setState({ plutoConfig: data });
      }
    } catch (error) {
      console.error(error);
    }

    this.setState(
      {
        isLoggedIn: valid,
      },
      () => {
        this.setState({ loading: false });
      }
    );
  }

  haveToken() {
    return window.localStorage.getItem("pluto:access-token");
  }

  oAuthConfigLoaded(oAuthConfig) {
    //If we already have a user token at mount, verify it and update our internal state.
    //If we do not, ignore for the time being; it will be set dynamically when the login occurs.
    console.log("Loaded oAuthConfig: ", oAuthConfig);
    if (this.haveToken()) {
      verifyExistingLogin(oAuthConfig)
        .then((profile) => this.setState({ userProfile: profile }))
        .catch((err) => {
          console.error("Could not verify existing user profile: ", err);
        });
    }
  }

  render() {
    return (
      <OAuthContextProvider onLoaded={this.oAuthConfigLoaded}>
        <UserContextProvider
          value={{
            profile: this.state.userProfile,
            updateProfile: (newValue) =>
              this.setState({ userProfile: newValue }),
          }}
        >
          <ThemeProvider theme={this.state.isDark ? darkTheme : lightTheme}>
            <CssBaseline />
            <Header></Header>
            <AppSwitcher onLoginValid={this.onLoginValid}></AppSwitcher>
            <div className="app">
              <div
                style={{
                  float: "right",
                  height: 0,
                  marginRight: "1em",
                  marginTop: "1em",
                  marginBottom: "-1em",
                }}
              >
                <IconButton
                  onClick={() =>
                    this.setState((prev) => ({ isDark: !prev.isDark }))
                  }
                >
                  {this.state.isDark ? <Brightness7 /> : <Brightness4 />}
                </IconButton>
              </div>
              <Routes>
                <Route
                  path="/log/:routename/:podname"
                  element={<MainWindow />}
                />
                <Route path="/log/:routename" element={<MainWindow />} />
                <Route
                  path="/logByJobName/:jobname"
                  element={<LogByJobName />}
                />
                <Route path="/log" element={<MainWindow />} />
                <Route path="/" element={<Navigate to="/log" replace />} />
              </Routes>
              <SystemNotification />
            </div>
          </ThemeProvider>
        </UserContextProvider>
      </OAuthContextProvider>
    );
  }
}
document.addEventListener("DOMContentLoaded", () => {
  render(
    <BrowserRouter basename={deploymentRootPath}>
      <App />
    </BrowserRouter>,
    document.getElementById("app")
  );
});
