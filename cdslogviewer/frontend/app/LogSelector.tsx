import React, { useState, useEffect } from "react";
import { TreeItem, TreeItemClassKey, TreeView } from "@material-ui/lab";
import axios from "axios";
import { formatError } from "./common/format_error";
import { ChevronRight, ExpandMore } from "@material-ui/icons";
import {
  CircularProgress,
  Grid,
  makeStyles,
  Typography,
} from "@material-ui/core";
import { loadLogsForRoute } from "./data-loading";
import { formatBytes } from "./common/bytesformatter";
import clsx from "clsx";

interface LogLabelProps {
  label: string;
  size: number;
  className?: string;
}

const LogLabel: React.FC<LogLabelProps> = (props) => {
  return (
    <Grid container direction="row" justify="space-between">
      <Grid item>
        <Typography className={props.className}>{props.label}</Typography>
      </Grid>
      <Grid item>
        <Typography className={props.className}>
          {formatBytes(props.size)}
        </Typography>
      </Grid>
    </Grid>
  );
};

interface RouteEntryProps {
  routeName: string;
  key: any;
  onError?: (errDesc: string) => void;
  logWasSelected: (routeName: string, logName: string) => void;
  loadingStatusChanged: (loadingStatus: boolean) => void;
}

const RouteEntry: React.FC<RouteEntryProps> = (props) => {
  const [childLogs, setChildLogs] = useState<LogInfo[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  const handleToggle = (evt: React.MouseEvent<Element, MouseEvent>) => {
    if (!isLoaded) {
      props.loadingStatusChanged(true);
      setIsLoaded(true);
      if (evt) evt.persist();
      console.log("loading new data");

      loadLogsForRoute(props.routeName, (newData) =>
        setChildLogs((prevState) => prevState.concat(newData))
      )
        .then(() => {
          if (evt) evt.target.dispatchEvent(evt.nativeEvent);
          props.loadingStatusChanged(false);
        })
        .catch((err) => {
          console.error(
            `Could not load in logs for route ${props.routeName}`,
            err
          );
          setIsLoaded(false);
          if (props.onError) props.onError(formatError(err, false));
        });
    }
  };

  return (
    <TreeItem
      nodeId={props.routeName}
      label={props.routeName}
      key={props.key}
      expandIcon={<ChevronRight />}
      endIcon={<ChevronRight />}
      onIconClick={handleToggle}
      onLabelClick={handleToggle}
    >
      {childLogs.map((info, idx) => (
        <TreeItem
          nodeId={info.name}
          //label={<Typography>{info.name} {formatBytes(info.size)}</Typography>}
          label={<LogLabel label={info.name} size={info.size} />}
          key={idx}
          onLabelClick={() => props.logWasSelected(props.routeName, info.name)}
        />
      ))}
    </TreeItem>
  );
};

interface LogSelectorProps {
  className?: string;
  selectionDidChange: (routeName: string, logName: string) => void;
  onError?: (errorDesc: string) => void;
  rightColumnExtent: number;
}

const useStyles = makeStyles((theme) => ({
  progressIndicator: {
    color: theme.palette.secondary.light,
    width: "20px",
    height: "20px",
  },
  container: {
    listStyle: "none",
    padding: 0,
    overflowY: "scroll",
    overflowX: "hidden",
  },
}));

const LogSelector: React.FC<LogSelectorProps> = (props) => {
  const [knownRoutes, setKnownRoutes] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const classes = useStyles();

  useEffect(() => {
    loadKnownRoutes();
  }, []);

  const loadKnownRoutes = async () => {
    try {
      const response = await axios.get<string[]>("/api/routes");
      setKnownRoutes(response.data.sort());
      setIsLoading(false);
    } catch (err) {
      setIsLoading(false);
      console.error("Could not list known routes: ", err);
      if (props.onError) {
        props.onError(formatError(err, false));
      }
    }
  };

  return (
    <ul className={clsx(props.className, classes.container)}>
      <li>
        <Grid container direction="row" justify="space-between">
          <Grid item>
            <Typography variant="h4">Jobs</Typography>
          </Grid>
          <Grid item>
            {isLoading ? (
              <CircularProgress className={classes.progressIndicator} />
            ) : null}
          </Grid>
        </Grid>
      </li>
      <li>
        <TreeView
          defaultExpandIcon={<ExpandMore />}
          defaultCollapseIcon={<ChevronRight />}
          defaultExpanded={[]}
        >
          {knownRoutes.length == 0 ? (
            <Typography variant="caption">No routes loaded</Typography>
          ) : (
            knownRoutes.map((name, idx) => (
              <RouteEntry
                routeName={name}
                key={idx}
                logWasSelected={props.selectionDidChange}
                loadingStatusChanged={(newStatus) => setIsLoading(newStatus)}
              />
            ))
          )}
        </TreeView>
      </li>
    </ul>
  );
};

export default LogSelector;
