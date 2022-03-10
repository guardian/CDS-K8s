import React, { useHistory } from "react";
import { RouteComponentProps, useParams } from "react-router";
import { loadLogForJobNameURL } from "./data-loading";

const LogByJobName: React.FC<RouteComponentProps> = (props) => {
  const { jobname } = useParams<{
    jobname: string;
  }>();

  const logURL = loadLogForJobNameURL(jobname);

  const history = useHistory();

  history.push(logURL);
};

export default LogByJobName;
