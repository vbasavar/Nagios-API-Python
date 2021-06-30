import requests
import pandas as pd
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

# You can change it to any delta of time but i used 5 hours for downtime.
end = int(datetime.timestamp(datetime.now() + timedelta(hours=5)))
start = int(datetime.timestamp(datetime.now()))

# you can add key value pairs of nagios server details
locations = {"<nagioshosts>": "<<add_your_key>>"}


# Need to pass ip address as list to verify whether they are present at nagios and retrieve the specific host name and location details if you have nagios 
# server present in multiple locations.
# We need pass list of ipaddress and fetch host_names as schedule downtime call require host_name as input.

def feth_nagios_data(host_lists):
    all_hosts = pd.DataFrame()
    for reg in locations.items():
        url = f"https://{reg[0]}/nagiosxi/api/v1/objects/hoststatus?apikey={reg[1]}&pretty=1"
        print(url)
        data = requests.get(url, verify=False)
        all_hosts_reg = pd.DataFrame(data.json()['hoststatus'])
        all_hosts_reg['loc'] = reg[0]
        all_hosts = all_hosts.append(all_hosts_reg.loc[all_hosts_reg.address.str.startswith("10.")])

    # This will come from external source
    all_hosts = all_hosts[all_hosts.address.isin(host_lists)][
        ['host_name', 'address', 'scheduled_downtime_depth', 'loc']]
    return all_hosts


# You need to pass the details retrieved using fetch_nagios_data along with comment of your own
def schedule_downtime(host_name, loc, comment="TESTING"):
    url = f"https://{loc}/nagiosxi/api/v1/system/scheduleddowntime?apikey={locations.get(loc)}&pretty=1"
    data = {"comment": comment,
            "start": start,
            "end": end,
            "hosts[]": host_name
            }
    try:
        stats = requests.post(url, data=data, verify=False)
    except Exception as e:
        print(f"Exception {e} occured while scheduling downtime on host {host_name}")
    else:
        if stats.status_code == 200:
            print(f"Successfully scheduled downtime on host {host_name} which is in location: {loc}")
        else:
            print(f"Failed to schedule downtime on host {host_name}")


# This will delete the downtime from the list of hosts which are added using the comment
# Here the comment acts as label to select the host and delete downtime from it.

# You can ignore line no 61 if you want to delete all the downtimes scheduled for the host but that is not recommended.
def delete_downtime(comment):
    del_hosts = pd.DataFrame()
    for reg in locations.items():
        url = f"https://{reg[0]}/nagiosxi/api/v1/objects/downtime?apikey={reg[1]}&pretty=1"
        downtime_entries = requests.get(url, verify=False)
        df = pd.DataFrame(downtime_entries.json()['scheduleddowntime'])
        df = df[df['comment_data'].str.lower() == comment.lower()]
        df['loc'] = reg[0]
        del_hosts = del_hosts.append(df)

    for i, k in del_hosts.iterrows():
        try:
            url = f"https://{k['loc']}/nagiosxi/api/v1/system/scheduleddowntime/{k['internal_id']}?apikey={locations.get(k['loc'])}&pretty=1"
            stats = requests.delete(url, verify=False)
        except Exception as e:
            print(f"Exception {e} occured while removing scheduled downtime on host {k['host_name']}")
        else:
            if stats.status_code == 200:
                print(
                    f"Successfully removed scheduled downtime on host {k['host_name']} which is in location: {k['loc']}")
            else:
                print(f"Failed to remove scheduled downtime  on host {k['host_name']}")


if __name__ == "__main__":
    nagios_data = feth_nagios_data()
    print(nagios_data)
    for i, k in nagios_data.iterrows():
        schedule_downtime(k['host_name'], k['loc'], "patching_process")
    delete_downtime("patching_process")  # You can comment this call to verify in the nagios console
