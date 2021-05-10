import React, { useEffect, useState } from "react";
import { makeStyles, Paper, Typography } from "@material-ui/core";
import clsx from "clsx";
import LogContent from "./logreader/LogContent";

interface LogReaderProps {
  className?: string;
  selectedLog?: SelectedLog;
}

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    height: "95%",
    padding: "1em",
  },
}));

const LogReader: React.FC<LogReaderProps> = (props) => {
  const classes = useStyles();

  return (
    <Paper elevation={3} className={clsx(props.className, classes.root)}>
      {props.selectedLog ? (
        <Typography variant="h4">
          {props.selectedLog.logName} from {props.selectedLog.route}
        </Typography>
      ) : (
        <Typography variant="h6">
          &lt;---- Please select a logfile in the list to the left
        </Typography>
      )}
      {props.selectedLog ? (
        <LogContent
          routeName={props.selectedLog.route}
          logName={props.selectedLog.logName}
        />
      ) : null}
    </Paper>
  );
};

export default LogReader;
