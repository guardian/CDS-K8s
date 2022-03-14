import React, { useState } from "react";
import { useParams, useHistory } from "react-router";
import { loadLogForJobNameURL } from "./data-loading";
import { SystemNotifcationKind, SystemNotification } from "pluto-headers";
import { formatError } from "./common/format_error";

interface LogByJobNameProps {
  className?: string;
}

const LogByJobName: React.FC<LogByJobNameProps> = (props) => {
  const { jobname } = useParams<{
    jobname: string;
  }>();

  const [logURL, setLogURL] = useState("");

  const forwardToURL = () => {
    loadLogForJobNameURL(jobname)
      .then((results) => {
        console.log(results);
        if (results != null) {
          setLogURL(results);
        }
        console.log(logURL);
        window.location.href = logURL;
      })
      .catch((err) => {
        console.error("Could not load log URL: ", err);
        SystemNotification.open(
          SystemNotifcationKind.Error,
          `Could not load log URL: ${formatError(err, false)}`
        );
      });
  };

  return <>{forwardToURL()}</>;
};

export default LogByJobName;
