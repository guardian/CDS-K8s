import React, { useState } from "react";
import { RouteComponentProps } from "react-router";
import { makeStyles } from "@material-ui/core";
import LogSelector from "./LogSelector";

const useStyles = makeStyles((theme) => ({
  baseGrid: {
    display: "grid",
    margin: "1em",
    gridTemplateColumns: "repeat(20, 5%)",
    gridTemplateRows: "[top] 200px [info-area] auto [bottom]",
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
    overflowX: "hidden",
    overflowY: "auto",
    marginRight: "1px solid",
    marginColor: theme.palette.primary.light,
  },
  logContent: {
    gridColumnStart: 4,
    gridColumnEnd: -1,
    gridRowStart: "info-area",
    gridRowEnd: "bottom",
    overflow: "auto",
  },
}));

const MainWindow: React.FC<RouteComponentProps> = (props) => {
  const classes = useStyles();
  const [loading, setLoading] = useState(true);
  const [lastError, setLastError] = useState<string | undefined>(undefined);

  const [selectedLog, setSelectedLog] = useState<string | undefined>(undefined);

  const logSelectionDidChange = (routeName:string, logName:string) => {
    console.log("Selected ", logName, " from " , routeName);
  }

  return (
    <div className={classes.baseGrid}>
      <div id="info-area" className={classes.infoArea} />
      <LogSelector
        selectionDidChange={logSelectionDidChange}
        className={classes.logSelector}
        rightColumnExtent={4}
      />
    </div>
  );
};

export default MainWindow;
