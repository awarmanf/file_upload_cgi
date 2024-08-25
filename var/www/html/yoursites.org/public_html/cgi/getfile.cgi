#!/usr/bin/perl -wT

#
# getfile.cgi
#
# Feautures
# 1. Support resuming download
# 2. Limit traffic download to spesific speed
# 3. Only allow one session download for unique ip address & user agent
#
# Created by Arief Yudhawarman
# (c) awarmanff@yahoo.com
#
# Revision: 14 Dec 2016

use strict;
use CGI;
use CGI::Carp qw(fatalsToBrowser);
use DBI;
use POSIX qw(strftime);
use Time::HiRes qw(sleep gettimeofday);

$CGI::DISABLE_UPLOADS   = 0;
$CGI::POST_MAX = 1024 * 5000; # 5 MB

# MySQL
my $DB   = 'upload';
my $HOST = 'localhost';
my $PORT = '3306';
my $USER = 'user1';
my $PASS = 'password1';
my $SEGMENT = 11584;  # ~ 112KB/s
 
my $safe_filename_characters = "a-zA-Z0-9_.-";
my $filedir = "/var/www/html/yoursites.org/files/";
my $rate = 5000; # asumsi rate upload in KB/s

my $buffer;
my @fileholder;

my $cgi = new CGI;

if (!$cgi->param('f')) {
  error ($cgi, "You must specify name of the file to download.");
} 

my ($fileSize, $fileRange, $lastMod, $differ, $differ2);
#
# $etime  : estimate time in seconds to download file with specified rate
# $stime  : time start of download plus microtime
#
my ($dbh, $sth, $rec, $id, $stime, $etime, $count);

my $filename = $cgi->param('f');
my $ip = $ENV{REMOTE_ADDR};
my $ua = $ENV{HTTP_USER_AGENT};

# remove trailing '/' or '\'
if ( $filename =~ /.*(\\|\/)(.*)/ ) {  
  $filename=$2 if ($2);  
}
$filename =~ tr/ /_/;
$filename =~ s/[^$safe_filename_characters]//g;
if ( $filename =~ /^([$safe_filename_characters]+)$/ )
{
  $filename = $1;
} else {
  error ($cgi, "Filename contains invalid characters");
}

if ($filename eq '') { 
  print "Content-type: text/html\n\n"; 
  print "You must specify a file to download."; 
} else {
  # cek ip and user agent user
  $dbh = DBI->connect("DBI:mysql:database=$DB;host=$HOST;port=$PORT", "$USER", "$PASS") || error($cgi, "Can not connect to database.");
  $sth = $dbh->prepare("SELECT COUNT(*) FROM log WHERE ip=? AND ua=?") || error($cgi, "Database error.");
  $sth->execute($ip,$ua);

  if ($count = $sth->fetchrow_array) {
    if ($count > 0 ) {
      $sth = $dbh->prepare("SELECT id FROM log WHERE ip=? AND ua=? AND status=FALSE") || error($cgi, "Database error.");
      $sth->execute($ip,$ua);
      if ($id = $sth->fetchrow_array) {
        # user is still downloading but do check if the download process is finished
        $sth = $dbh->prepare("SELECT stime,etime FROM log WHERE id=?") || error($cgi, "Database error.");
        $sth->execute($id);
        $rec = $sth->fetchrow_hashref;
        $stime = $rec->{stime};
        # epoch 
        my ($now, $usec) = gettimeofday();
        if ( $now > $stime+$etime ) {
          # upload is done
          $sth = $dbh->prepare("UPDATE log SET status=TRUE WHERE id=?") || error($cgi, "Database error.");
          $sth->execute($id);
          # user may download
          upload($ip,$ua,$filename);
        } else {
          # user deny download
          error($cgi, "Your download session is still progressing.");
        }        
      } else {
        upload($ip,$ua,$filename);
      }
    } else {
      upload($ip,$ua,$filename);
    }
  } else {
      upload($ip,$ua,$filename);
#error($cgi, "Akses 5.")
  }
}

#
# Functions
#

sub upload {
  ($ip, $ua, $filename) = @_;
  ($fileSize) = (stat("$filedir/$filename"))[7]; # bytes
  $etime = $fileSize / $rate / 1024;
  
  $sth = $dbh->prepare("INSERT INTO log (ip,ua,stime,etime) VALUES (?,?,?,?)") || error($cgi, "Database error.");
  my ($s, $usec) = gettimeofday();
  $sth->execute($ip,$ua,$s+($usec/1000000),$etime);
  # get last insert id
  $sth = $dbh->prepare("SELECT LAST_INSERT_ID()") || error($cgi, "Database error.");
  $sth->execute();
  $id = $sth->fetchrow_array;

  open(FH, "<$filedir/$filename") || error($cgi, "Error open file or file $filename not found."); 
  binmode FH;

  ($lastMod) = (stat("$filedir/$filename"))[9];
  $lastMod = epoch2datetime($lastMod);

  if (exists $ENV{HTTP_RANGE}) {
    $fileRange = $& if ($ENV{HTTP_RANGE} =~ /\d+/);
    $differ = $fileSize - $fileRange;  
    $differ2 = $fileSize - 1;  
    print $cgi->header(-status=>"206 Partial Content",
                       -type=>"application/x-download",
                       -Last_Modified=>$lastMod,
                       -Accept_Ranges=>"bytes",
                       -Content_Length=>$differ,
                       -Content_Range=>"bytes $fileRange-$differ2/$fileSize",
                       -Connection=>"close",
                       -Content_Disposition=>"attachment;filename=$filename"
                      );
    seek FH, $fileRange, 1;
  } else {
    print $cgi->header(-status=>"200 OK",
                       -type=>"application/x-download",
                       -Last_Modified=>$lastMod,
                       -Accept_Ranges=>"bytes",
                       -Content_Length=>$fileSize,
                       -Connection=>"close",
                       -Content_Disposition=>"attachment;filename=$filename"
                      );
  }

  while ( my $read = sysread(FH, $buffer, $SEGMENT) ) {
    print $buffer;
    sleep 0.1;
  }
  close (FH) || error ($cgi, 'Error close file');
  # upload is done
  $sth = $dbh->prepare("UPDATE log SET status=TRUE WHERE id=?") || error($cgi, "Database error.");
  $sth->execute($id);
  # save history of getfile 
  $sth = $dbh->prepare("INSERT INTO getfile (filename,ua,ip) VALUES (?,?,?)") || error($cgi, "Database error.");
  $sth->execute($filename,$ua,$ip);
}

sub error {
  my ($cgi, $reason ) = @_;
  
  print $cgi->header( "text/html" ),
        $cgi->start_html( "Error" ),
        $cgi->h1( "Error" ),
        $cgi->p( "Your download was not processed because the following error ",
               "occured: " ),
        $cgi->p($cgi->i($reason) ),
        $cgi->end_html;
  exit;
}

sub epoch2datetime {
  my ($epoch) = @_;
  # disable timezone like this output
  # Last Modified: Thu, 19 Oct 2017 16:22:00 WIB
  # because wget complain "Last-modified header invalid — time-stamp ignored"
  # but when timezone using WIT it doesn't complain
  #return (strftime "%a, %e %b %Y %H:%M:%S %Z", localtime($epoch));
  return (strftime "%a, %e %b %Y %H:%M:%S", localtime($epoch));
}
