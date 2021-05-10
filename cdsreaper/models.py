import redis
import json
import time
import logging

logger = logging.getLogger(__name__)


class JobState(object):
    def __init__(self,uid:str, name:str, status:str, timestamp:float):
        self.uid = uid
        self.name = name
        self.status = status
        self.float = timestamp if timestamp else time.time()

    def to_json(self):
        return json.dumps(self.__dict__)

    def key(self):
        return "cds:job:{0}".format(self.uid)

    def write(self, client:redis.client.Redis):
        client.set(self.key(), self.to_json())

    def delete(self, client:redis.client.Redis):
        client.delete(self.key())

    @staticmethod
    def read(client:redis.client.Redis, uid:str):
        """
        look up the given job uid in the datastore. Returns the object as JobState or None.
        :param client:
        :param uid:
        :return:
        """
        key = "cds:job:{0}".format(uid)
        json_data = client.get(key)
        if json_data is not None:
            try:
                parsed_dict = json.loads(json_data)
                return JobState(parsed_dict["uid"],parsed_dict["name"],parsed_dict["status"], parsed_dict["timestamp"])
            except KeyError as e:
                logger.error("Data for job {0} was invalid, missing key {1}.".format(uid, str(e)))
                client.delete(key)
                return None
            except json.JSONDecodeError as e:
                logger.error("Data for job {0} was invalid, not a correct json object: {1}".format(uid, str(e)))
                client.delete(key)
                return None
        else:
            return None