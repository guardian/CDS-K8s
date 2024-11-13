import React from "react";
import { useParams, useNavigate } from "react-router";
import { loadLogForJobNameURL } from "./data-loading";
import {
  SystemNotifcationKind,
  SystemNotification,
} from "@guardian/pluto-headers";
import { formatError } from "./common/format_error";

interface LogByJobNameProps {
  className?: string;
}

const LogByJobName: React.FC<LogByJobNameProps> = (props) => {
  const { jobname } = useParams<{
    jobname: string;
  }>();

  const history = useNavigate();

  const forwardToURL = () => {
    if (jobname) {
      loadLogForJobNameURL(jobname)
        .then((result) => {
          history(result);
        })
        .catch((err) => {
          console.error("Could not load log URL: ", err);
          SystemNotification.open(
            SystemNotifcationKind.Error,
            `Could not load log URL: ${formatError(err, false)}`
          );
        });
    } else {
      console.error("Job name is undefined");
      SystemNotification.open(
        SystemNotifcationKind.Error,
        "Job name is undefined"
      );
    }
  };

  return <>{forwardToURL()}</>;
};

export default LogByJobName;
