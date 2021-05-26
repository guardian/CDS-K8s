import React, { useState, useEffect } from "react";
import { TreeItem, TreeItemClassKey, TreeView } from "@material-ui/lab";
import axios from "axios";
import { formatError } from "./common/format_error";
import {
  ArrowDropDown,
  ChevronRight,
  ExpandMore,
  KeyboardArrowDown,
  Replay,
} from "@material-ui/icons";
import {
  CircularProgress,
  Grid,
  IconButton,
  makeStyles,
  setRef,
  Typography,
} from "@material-ui/core";
import { loadLogsForRoute } from "./data-loading";
import { formatBytes } from "./common/bytesformatter";
import clsx from "clsx";
import { useHistory, useParams } from "react-router";

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
  childKey: any;
  refreshGeneration: number;
  onError?: (errDesc: string) => void;
  logWasSelected: (routeName: string, logName: string) => void;
  loadingStatusChanged: (loadingStatus: boolean) => void;
}

const RouteEntry: React.FC<RouteEntryProps> = (props) => {
  const [childLogs, setChildLogs] = useState<LogInfo[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    if (props.refreshGeneration > 0) {
      //we are called on initial load, which is handled below
      setChildLogs([]);
      loadLogsForRoute(props.routeName, (newData) =>
        setChildLogs((prevState) => prevState.concat(newData))
      ).catch((err) => {
        console.log("Could not load in logs for ", props.routeName, ": ", err);
      });
    }
  }, [props.refreshGeneration]);

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
      key={props.childKey}
      expandIcon={<ChevronRight />}
      collapseIcon={<KeyboardArrowDown />}
      endIcon={<ChevronRight />}
      onIconClick={handleToggle}
      onLabelClick={handleToggle}
    >
      {childLogs.map((info, idx) => (
        <TreeItem
          nodeId={info.name}
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
  onError?: (errorDesc: string) => void;
  onNotLoggedIn?: () => void;
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
  spinner: {
    animation: "1.5s linear infinite spinner",
  },
}));

const LogSelector: React.FC<LogSelectorProps> = (props) => {
  const [knownRoutes, setKnownRoutes] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expanded, setExpanded] = React.useState<string[]>([]);
  const [selected, setSelected] = React.useState<string>("");
  const [refreshGeneration, setRefreshGeneration] = useState(0);

  const classes = useStyles();

  const { routename, podname } = useParams<{
    routename: string | undefined;
    podname: string | undefined;
  }>();
  const history = useHistory();

  useEffect(() => {
    loadKnownRoutes();
  }, []);

  useEffect(() => {
    if (knownRoutes.length > 0) {
      console.log(
        "logSelector: updated routename is ",
        routename,
        " routes are ",
        knownRoutes
      );
      if (routename) setExpanded([routename]);
    }
  }, [routename, knownRoutes]);

  useEffect(() => {
    if (knownRoutes.length > 0) {
      console.log("logSelector: updated podname is ", podname);
      if (podname) setSelected(podname);
    }
  }, [podname, knownRoutes]);

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
      if (err.response && props.onNotLoggedIn) {
        if (err.response.status == 403 || err.response.status == 401)
          props.onNotLoggedIn();
      }
    }
  };

  const logSelectionDidChange = (routeName: string, logName: string) => {
    console.log("Selected ", logName, " from ", routeName);
    history.push(`/log/${routeName}/${logName}`);
  };

  const handleToggle = (event: React.ChangeEvent<{}>, nodeIds: string[]) => {
    setExpanded(nodeIds);
  };

  const handleSelect = (event: React.ChangeEvent<{}>, nodeIds: string) => {
    setSelected(nodeIds);
  };

  console.log(
    "render: expanded is ",
    expanded,
    " known routes are ",
    knownRoutes
  );

  const refreshLogSelector = async () => {
    setIsLoading(true);
    await loadKnownRoutes();
    setRefreshGeneration((prev) => prev + 1);
    setIsLoading(false);
  };

  return (
    <ul className={clsx(props.className, classes.container)}>
      <li>
        <Grid container direction="row" justify="space-between">
          <Grid item>
            <Typography variant="h4">Jobs</Typography>
          </Grid>
          <Grid item>
            <IconButton onClick={refreshLogSelector}>
              <Replay className={isLoading ? classes.spinner : undefined} />
            </IconButton>
          </Grid>
        </Grid>
      </li>
      <li>
        <TreeView
          defaultExpandIcon={<ExpandMore />}
          defaultCollapseIcon={<ChevronRight />}
          expanded={expanded}
          selected={selected}
          onNodeToggle={handleToggle}
          onNodeSelect={handleSelect}
        >
          {knownRoutes.length == 0 ? (
            <Typography variant="caption">No routes loaded</Typography>
          ) : (
            knownRoutes.map((name, idx) => (
              <RouteEntry
                routeName={name}
                refreshGeneration={refreshGeneration}
                childKey={idx}
                key={idx}
                logWasSelected={logSelectionDidChange}
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
