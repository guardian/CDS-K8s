import React, { useEffect, useState } from "react";
import { RouteComponentProps, useParams } from "react-router";
import { makeStyles, Typography } from "@material-ui/core";
import LogSelector from "./LogSelector";
import LogReader from "./LogReader";
import Helmet from "react-helmet";

const useStyles = makeStyles((theme) => ({
  baseGrid: {
    display: "grid",
    paddingLeft: "1em",
    paddingRight: "1em",
    overflow: "hidden",
    gridTemplateColumns: "repeat(20, 5%)",
    gridTemplateRows: "[top] 80px [info-area] auto [bottom]",
    height: "85vh",
    width: "98vw",
  },
  infoArea: {
    gridColumnStart: 4,
    gridColumnEnd: -1,
    gridRowStart: "top",
    gridRowEnd: "info-area",
  },
  logSelector: {
    gridColumnStart: 1,
    gridColumnEnd: 4,
    gridRowStart: "top",
    gridRowEnd: "bottom",
    paddingRight: "1em",
    borderRight: "1px solid",
    borderColor: theme.palette.primary.light,
  },
  logContent: {
    gridColumnStart: 4,
    gridColumnEnd: -1,
    gridRowStart: "info-area",
    gridRowEnd: "bottom",
    paddingLeft: "1em",
    marginLeft: "1em",
    overflow: "auto",
  },
}));

const MainWindow: React.FC<RouteComponentProps> = (props) => {
  const classes = useStyles();
  const [isLoggedIn, setIsLoggedIn] = useState(true);

  const [selectedLog, setSelectedLog] = useState<SelectedLog | undefined>(
    undefined
  );

  return (
    <>
      <Helmet>
        {selectedLog ? (
          <title>{selectedLog.logName} - CDS Logs</title>
        ) : (
          <title>CDS Log Viewer</title>
        )}
      </Helmet>
      {isLoggedIn ? (
        <div className={classes.baseGrid}>
          <div id="info-area" className={classes.infoArea}>
            <Typography style={{ textAlign: "center" }} variant="h2">
              Content delivery logs
            </Typography>
          </div>

          <LogSelector
            className={classes.logSelector}
            rightColumnExtent={4}
            onNotLoggedIn={() => setIsLoggedIn(false)}
          />
          <LogReader className={classes.logContent} />
        </div>
      ) : (
        <div className={classes.baseGrid}>
          <div id="info-area" className={classes.infoArea}>
            <Typography style={{ textAlign: "center" }}>
              You are either not logged in, or not an administrator. Log in
              using the button above to continue.
            </Typography>
          </div>
        </div>
      )}
    </>
  );
};

export default MainWindow;
