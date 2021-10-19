
# Example 3 - Work with a remote system

This is a simple example to show how DiffSync can be used to compare and synchronize data with a remote system like [Nautobot](https://nautobot.readthedocs.io) via a REST API.

For this example, we have a shared model for Region and Country defined in `models.py`.
A country must be part of a region and has an attribute to capture its population.

The comparison and synchronization of dataset is done between a local JSON file and the [public instance of Nautobot](https://demo.nautobot.com).

Also, this example is showing :
- How to set a Global Flags to ignore object that are not matching 
- How to provide a custom Diff class to change the ordering of a group of object

> The source code for this example is in Github in the [examples/03-remote-system/](https://github.com/networktocode/diffsync/tree/main/examples/03-remote-system) directory.

## Install the requirements

to use this example you must have some dependencies installed, please make sure to run 
```
pip install -r requirements.txt
```

## Setup the environment

By default this example will interact with the public sandbox of Nautobot at https://demo.nautobot.com but you can use your own version of Nautobot by providing a new URL and a new API token using the environment variables `NAUTOBOT_URL` & `NAUTOBOT_TOKEN`

```
export NAUTOBOT_URL = "https://demo.nautobot.com"
export NAUTOBOT_TOKEN = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
```

## Try the example

The first time you run this example, a lot of changes should be reported between Nautobot and the local data because by default the demo instance doesn't have the subregion defined.
After the first sync, on subsequent runs, the diff should show no changes. 
At this point, `Diffsync` will be able to identify and fix all changes in Nautobot. You can try to add/update or delete any country in Nautobot and DiffSync will automatically catch it and it will fix it with running in sync mode.

```
### DIFF Compare the data between Nautobot and the local JSON file.
python main.py --diff

### SYNC Update the list of country in Nautobot.
python main.py --sync
```

