import React, { useState } from "react";
import { RouteComponentProps } from "react-router";
import { makeStyles } from "@material-ui/core";
import LogSelector from "./LogSelector";
import LogReader from "./LogReader";
import Helmet from "react-helmet";

const useStyles = makeStyles((theme) => ({
  baseGrid: {
    display: "grid",
    margin: "1em",
    marginLeft: "auto",
    marginRight: "auto",
    overflow: "hidden",
    gridTemplateColumns: "repeat(20, 5%)",
    gridTemplateRows: "[top] 200px [info-area] auto [bottom]",
    height: "95vh",
    width: "98vw"
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
    gridRowStart: "top",
    gridRowEnd: "bottom",
    paddingLeft: "1em",
    overflow: "auto",
  },
}));

const MainWindow: React.FC<RouteComponentProps> = (props) => {
  const classes = useStyles();
  const [loading, setLoading] = useState(true);
  const [lastError, setLastError] = useState<string | undefined>(undefined);

  const [selectedLog, setSelectedLog] = useState<SelectedLog | undefined>(undefined);

  const logSelectionDidChange = (routeName:string, logName:string) => {
    console.log("Selected ", logName, " from " , routeName);
    setSelectedLog({
      route: routeName,
      logName: logName
    })
  }

  return (
      <>
        <Helmet>
          {
            selectedLog ? <title>{selectedLog.logName} - CDS Logs</title> : <title>CDS Log Viewer</title>
          }
        </Helmet>
    <div className={classes.baseGrid}>
      <div id="info-area" className={classes.infoArea} />
      <LogSelector
        selectionDidChange={logSelectionDidChange}
        className={classes.logSelector}
        rightColumnExtent={4}
      />
      <LogReader className={classes.logContent} selectedLog={selectedLog}/>
    </div>
        </>
  );
};

export default MainWindow;
