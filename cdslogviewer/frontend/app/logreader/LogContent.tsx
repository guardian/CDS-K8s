import React, { useState, useEffect, useRef } from "react";
import { makeStyles, Select, Typography } from "@material-ui/core";
import { loadMoreLogLines } from "../data-loading";
import { parseISO, formatDistanceToNow, isFuture } from "date-fns";

interface LogContentProps {
  routeName: string;
  logName: string;
  refreshTimeout?: number; //in ms
  onError?: (errorDesc: string) => void;
}

const useStyles = makeStyles((theme) => ({
  logContainer: {
    backgroundColor: theme.palette.logviewer.background,
    color: theme.palette.logviewer.main,
    listStyle: "none",
    height: "90%",
    marginRight: "1em",
    overflow: "auto",
  },
  logBlock: {
    fontFamily: ["Courier", "Courier New", "serif"].join(","),
  },
}));

const LogContent: React.FC<LogContentProps> = (props) => {
  const [loadedLineCount, setLoadedLineCount] = useState(0);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastModified, setLastModified] = useState<Date | undefined>(undefined);

  const classes = useStyles();

  const loadedLineCountRef = useRef<number>();
  loadedLineCountRef.current = loadedLineCount;

  useEffect(() => {
    const timerId = window.setInterval(
      regularUpdate,
      props.refreshTimeout ?? 3000
    );
    loadedLineCountRef.current = 0;
    regularUpdate();

    return () => {
      setLogLines([]);
      setLoadedLineCount(0);
      window.clearInterval(timerId);
    };
  }, [props.routeName, props.logName]);

  const regularUpdate = () => {
    loadMoreLogLines(
      props.routeName,
      props.logName,
      loadedLineCountRef.current ?? 0
    )
      .then((results) => {
        setIsLoading(false);
        if (results.lastModified) {
          try {
            setLastModified(parseISO(results.lastModified));
          } catch (e) {
            console.error(
              "Could not parse last modified string ",
              results.lastModified,
              ": ",
              e
            );
          }
        }
        if (results.count > 0) {
          console.log(`Received ${results.count} more log lines`);
          setLoadedLineCount((prevValue) => prevValue + results.count);
          setLogLines((prevValue) => prevValue.concat(...results.content));
        } else {
          console.log("Received no more extra content");
        }
      })
      .catch((err) => {
        console.error("Could not load in more log lines: ", err);
        if (props.onError) props.onError(err.toString());
      });
  };

  const lastModifiedString = () => {
    if (lastModified) {
      let timestr;
      if (isFuture(lastModified)) {
        timestr = `is in ${formatDistanceToNow(lastModified)}`;
      } else {
        timestr = `was ${formatDistanceToNow(lastModified)} ago`;
      }
      return `Last update ${timestr}`;
    } else {
      return "";
    }
  };

  return (
    <>
      <Typography>
        Auto-refresh is enabled for the log. {lastModifiedString()}
      </Typography>
      <div className={classes.logContainer}>
        <pre className={classes.logBlock}>{logLines.join("\n")}</pre>
      </div>
    </>
  );
};

export default LogContent;
