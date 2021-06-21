import React, { useEffect, useState } from "react";
import { makeStyles, Paper, Typography } from "@material-ui/core";
import clsx from "clsx";
import LogContent from "./logreader/LogContent";
import { useParams } from "react-router";

interface LogReaderProps {
  className?: string;
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

  const { routename, podname } = useParams<{
    routename: string | undefined;
    podname: string | undefined;
  }>();

  return (
    <Paper elevation={3} className={clsx(props.className, classes.root)}>
      {routename && podname ? (
        <Typography variant="h4">
          {podname} from {routename}
        </Typography>
      ) : (
        <Typography variant="h6">
          &lt;---- Please select a logfile in the list to the left
        </Typography>
      )}
      {routename && podname ? (
        <LogContent routeName={routename} logName={podname} />
      ) : null}
    </Paper>
  );
};

export default LogReader;
