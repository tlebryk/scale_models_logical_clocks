```bash
git checkout demo
git pull 
cd src 
docker-compose up --build
```
Show the logs in logs/demo1 and make remarks (feel free to show notebook results).

Next, show experiment with smaller chance of an internal action.
```bash
docker-compose -f docker-compose-5_max_action.yaml up --build

```
Show logs in logs/5_max_action with commentary from notebook.

Show experiment with less variability in clock speed. 
```bash
docker-compose -f docker-compose-tight.yaml up --build

```
Show logs in logs/tight with commentary from notebook.

Last, show experiment with four machines. 
```bash
git checkout 4-per
docker-compose up --build
```