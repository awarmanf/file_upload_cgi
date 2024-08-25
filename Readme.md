
# File Upload CGI

The File Upload CGI is a web application written in Perl CGI to limit the upload rate of a file to user.

>This application is written on Debian Linux (Jessie).

## Features

* Support resuming download
* Limit traffic download user to specified speed
* Only allow one session download for unique ip address & user agent

## Requirement

You must install nginx, mysql and perl cgi.

Configure nginx to use `rewrite` rule. Edit file `/etc/nginx/sites-enabled/default`

```nginx
server {
  listen 80;
  listen [::]:80;

  # SSL configuration
  #
  listen 443 ssl;
  listen [::]:443 ssl;
  include snippets/yoursites.org.conf;

  server_name yoursites.org;
  access_log /var/www/html/yoursites.org/logs/access.log;
  error_log /var/www/html/yoursites.org/logs/error.log;

  root   /var/www/html/yoursites.org/public_html;
  index  index.html index.htm index.php;

  rewrite ^/files/(.*)$ /cgi/getfile.cgi?f=$1 last;

  include php-fastcgi;
  include perl-fastcgi;
}
```

## Create directory for hostname yoursites.org

```
mkdir /var/www/html/yoursites.org
mkdir /var/www/html/yoursites.org/{files,logs,public_html,public_html/cgi}
```

Save the script `getfile.cgi` at directory `/var/www/html/yoursites.org/public_html/cgi`

## Create database upload

Login to mysql as user root

```sql
CREATE DATABASE upload;
CREATE USER 'user1'@'localhost' IDENTIFIED BY 'password1';
GRANT ALL PRIVILEGES ON `smscgi` . * TO 'user1'@'localhost';
QUIT;
```

Then execute sql statements on file `smscgi.db`

```
mysql -u user1 -p upload < upload.db
```

## Create file dummy

Create file dummy 1MB and 10MB and save at directory `/var/www/html/yoursites.org/files`

```
DST=/var/www/html/yoursites.org/files
dd if=/dev/urandom of=${DST}/file-1MB.dat bs=1M count=1
dd if=/dev/urandom of=${DST}/file-10MB.dat bs=1M count=10
```

## Test download file

Restart nginx

```
/etc/init.d/nginx restart
```

Using wget download the file `file-1MB.dat`

```
$ wget http://yoursites.org/files/file-1MB.dat
--2024-08-25 15:34:15--  http://yoursites.org/files/file-1MB.dat
Resolving yoursites.org (yoursites.org)... 1.2.3.4
Connecting to yoursites.org (yoursites.org)|1.2.3.4|:80... connected.
HTTP request sent, awaiting response... 200 OK
Length: 1048576 (1,0M) [application/x-download]
Saving to: ‘file-1MB.dat’

file-1MB.dat           100%[==================================>]   1,00M   112KB/s    in 9,1s    

2024-08-25 15:34:24 (112 KB/s) - ‘file-1MB.dat’ saved [1048576/1048576]
```

## Show log upload

```sql
mysql> select * from getfile;
+----+---------------+-------------+------------+---------------------+
| id | filename      | ua          | ip         | date                |
+----+---------------+-------------+------------+---------------------+
| 1  | file-10MB.dat | Wget/1.21.2 | 103.47.1.2 | 2024-08-25 17:01:10 |
| 2  | file-10MB.dat | Wget/1.21.2 | 103.47.1.2 | 2024-08-25 17:02:17 |
+----+---------------+-------------+------------+---------------------+
2 rows in set (0.01 sec)

mysql> select * from log limit 3701,3703;
+----+------------+-------------+------------------+-------+--------+
| id | ip         | ua          | stime            | etime | status |
+----+------------+-------------+------------------+-------+--------+
| 1  | 103.47.1.2 | Wget/1.21.2 | 1724579980.00809 |     2 |      1 |
| 2  | 103.47.1.2 | Wget/1.21.2 | 1724580083.71145 |     2 |      1 |
+----+------------+-------------+------------------+-------+--------+
2 rows in set (0.00 sec)
```


