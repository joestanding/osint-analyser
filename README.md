# OSINT Collector and Analyser

This tool is designed to support the collection of open source intelligence (OSINT) for storage and analysis using Large Language Models (LLMs). Currently, support for collection via Telegram is included, with OpenAI's GPT as an analysis backend.

It can be used to perform automated analysis on a wide variety of collected text data. For example, an LLM can be tasked with producing a three bulletpoint summary for all messages received in a certain Telegram channel. The tool will also perform translation of non-English textual material, enabling easier comprehension and greater analytic capability for language models that are primarily trained on English material.

Different sources can be handled differently, for example a Telegram channel covering the Israel-Gaza conflict can be assigned one subset of analytic requirements, while a channel about the Russia-Ukraine conflict can be assigned an entirely different set of analytic requirements. This can be useful, as requirements may be considerably different - for example, a requirement to summarise territorial changes in the south of Ukraine would not be applicable to text content retrieved from a channel about Israel/Gaza.

## Requirements
The tool is currently dockerised, requiring Docker and Docker Compose. The tool should be relatively portable provided these requirements are present.

## Adding Analysis Requirements
Currently, additional analysis requirements must be added to the database directly using the MySQL client. You can connect to the MySQL instance with the following command:

```
# Identify the MySQL container ID
$ docker ps
CONTAINER ID   IMAGE                                COMMAND                  CREATED          STATUS                    PORTS
...
54fd2a481282   mysql:latest                         "docker-entrypoint.s…"   45 seconds ago   Up 44 seconds (healthy)   3306/tcp, 33060/tcp
...
$ docker exec -it <mysql container id> mysql -u root -p osint
mysql>
```

The format of the analysis requirement table is as follows:
```
mysql> DESCRIBE analysis_requirement;
+-----------+--------------+------+-----+---------+----------------+
| Field     | Type         | Null | Key | Default | Extra          |
+-----------+--------------+------+-----+---------+----------------+
| id        | int          | NO   | PRI | NULL    | auto_increment |
| source_id | int          | NO   | MUL | NULL    |                |
| llm_id    | int          | NO   |     | NULL    |                |
| name      | varchar(255) | NO   |     | NULL    |                |
| prompt    | text         | YES  |     | NULL    |                |
| enabled   | tinyint(1)   | YES  |     | NULL    |                |
+-----------+--------------+------+-----+---------+----------------+
```

After translation, the collector will issue an analysis task, which will consult the analysis requirements table to identify any requirements with a corresponding source ID. The LLM chosen for analysis will receive the prompt specified in the database record as instruction on how to analyse the message. The collected message will then also be passed to the LLM for it to act upon.


## Installation

Running the collector should be as simple as bringing the Docker environment up with the following command, executed in the project's root directory:

`$ docker compose up`

Log output from each of the containers should then be visible, including debugging information from the collectors and analysers.
