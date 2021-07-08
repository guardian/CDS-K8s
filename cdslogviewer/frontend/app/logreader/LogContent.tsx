import React, { useState, useEffect, useRef } from "react";
import {
  FormControlLabel,
  makeStyles,
  Switch,
  Typography,
} from "@material-ui/core";
import { loadMoreLogLines } from "../data-loading";
import { parseISO, formatDistanceToNow, isFuture } from "date-fns";
import { SystemNotification, SystemNotifcationKind } from "pluto-headers";
import {formatError} from "../common/format_error";

interface LogContentProps {
  routeName: string;
  logName: string;
  refreshTimeout?: number; //in ms
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
  const [scrollToBottom, setScrollToBottom] = useState(true);
  const classes = useStyles();

  let logEnd: HTMLDivElement | null = null;

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
        SystemNotification.open(SystemNotifcationKind.Error, `Could not load in more log lines: ${formatError(err, false)}`);
      });
  };

  /**
   * if the user wants us to, scroll to the end of the log whenever the log lines change or when they check 'Keep in view'
   */
  useEffect(() => {
    if (scrollToBottom && logEnd) {
      logEnd.scrollIntoView({ behavior: "smooth" });
    }
  }, [logLines, scrollToBottom]);

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
      <FormControlLabel
        label="Keep end of log in view"
        control={
          <Switch
            checked={scrollToBottom}
            onChange={(evt) => setScrollToBottom(evt.target.checked)}
          />
        }
      />
      <Typography>
        Auto-refresh is enabled for the log. {lastModifiedString()}
      </Typography>
      <div className={classes.logContainer}>
        <pre className={classes.logBlock}>{logLines.join("\n")}</pre>
        <div
          style={{ float: "left", clear: "both" }}
          ref={(el) => {
            logEnd = el;
          }}
        />
      </div>
    </>
  );
};

export default LogContent;
