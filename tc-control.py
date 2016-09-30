import os
import socket
import time
import MySQLdb as mysql
from urlparse import parse_qs
from subprocess import call

# Basic Settings
USER_EXT = '5555'
USER_PWD = 'somepassword'
AMI_USER = 'amiuser'
AMI_SECRET = 'amipassword'
MYSQL_HOST = 'localhost'
MYSQL_USER = 'mysqluser'
MYSQL_PASS = 'mysqlpass'
MYSQL_DB = 'asterisk' # Change this if you created a MySQL/MariaDB Database under a different name.

# Advanced Settings
NET_WAIT_TIME = .02
NET_AMI_ADDRESS = ('127.0.0.1', 5038)
BUFFER_LEN = 1024
FREEPBX_RELOAD_ARGS = ['/var/lib/asterisk/bin/module_admin', 'reload']
###############################################################################################

LOGIN_MESSAGE = '''\
Action: login
Username: {ami_user}
Secret: {ami_secret}
Events: off

'''.format(ami_user=AMI_USER, ami_secret=AMI_SECRET)

LOGOFF_MESSAGE = '''\
Action: Logoff

'''

STYLE = '''\
<title>Time Condition</title>
  <style>

  body {
    background-color: #555555;
  }

  .center {
    margin-left: auto;
    margin-right: auto;
    text-align: center;
  }

  .first {
    margin-top: 50px;
  }

  .message {
    background-color: #a18dfc;
    border: 2px solid #42d4f4;
    box-shadow: 0 0 15px blue, 0 0 20px blue;
    border-radius: 15px;
  }

  .select_group {
    line-height: 0.5;
  }

  button {
    margin-top: 20px;
    font-size: 15px;
  }

  button > a {
    color: #000000;
    text-decoration: none;
  }

  button.left {
    margin-right: 25px;
  }

  .small {
    font-size: 12px;
  }

  .up {
    margin-top: -10px;
  }

  </style>'''

def get_db_value(tc):
    try:
        int(tc)
    except ValueError:
        return
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(NET_AMI_ADDRESS)
    string_template = {'tc':tc}
    db_get_message = '''\
Action: DBGet
Family: TC
Key: {tc}

'''.format(**string_template)
    s.send(LOGIN_MESSAGE)
    time.sleep(NET_WAIT_TIME)
    login_response = s.recv(BUFFER_LEN)
    if 'Success' not in login_response:
        return
    s.send(db_get_message)
    time.sleep(NET_WAIT_TIME)
    response = s.recv(BUFFER_LEN)
    s.send(LOGOFF_MESSAGE)
    time.sleep(NET_WAIT_TIME)
    s.recv(BUFFER_LEN)
    s.close()
    if 'Success' not in response:
        return
    start_flag = 'Val: '
    end_flag = '\r\n'
    index_start = response.index(start_flag) + len(start_flag)
    index_end = response.index(end_flag, index_start)
    value = response[index_start:index_end]
    return value

def set_db_value(tc, value):
    try:
        int(tc)
    except ValueError:
        return
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(NET_AMI_ADDRESS)
    string_template = {'tc':tc, 'value':value}
    db_put_message = '''\
Action: DBPut
Family: TC
Key: {tc}
Val: {value}

'''.format(**string_template)
    s.send(LOGIN_MESSAGE)
    time.sleep(NET_WAIT_TIME)
    login_response = s.recv(BUFFER_LEN)
    if 'Success' not in login_response:
        return
    s.send(db_put_message)
    time.sleep(NET_WAIT_TIME)
    response = s.recv(BUFFER_LEN)
    s.send(LOGOFF_MESSAGE)
    time.sleep(NET_WAIT_TIME)
    s.recv(BUFFER_LEN)
    s.close()
    if 'Success' not in response:
        return
    return value

def get_index(tc):
    tc_state = 'ON'
    other_state = 'Off'
    value = get_db_value(tc)
    if value is None:
        return 'Problem Getting DB Value'
    
    if value.startswith('false'):
        tc_state = 'OFF'
        other_state = 'On'
    html_string = '''\
<head>
{style}
  <script type="text/javascript">
'''.format(style=STYLE)

    string_template = {'user':USER_EXT, 'pwd':USER_PWD, 'tc':tc, 'other_state':other_state}
    url_part = 'toggle_state?user={user}&pwd={pwd}&tc={tc}&other_state={other_state}'.format(**string_template)
    url_whole = os.path.join(BASE_URL_DIRECTORY, url_part)
    html_string += '''
    function change_state() {{
      window.open("{url}", "_self");
    }}
'''.format(url=url_whole)

    url_part = 'time_edit?user={user}&pwd={pwd}&tc={tc}'.format(**string_template)
    url_whole = os.path.join(BASE_URL_DIRECTORY, url_part)
    html_string += '''
    function edit_time() {{
      window.open("{url}", "_self");
    }}
'''.format(url=url_whole)
    html_string += '''
  </script>
</head>'''

    string_template = {
        'tc_state':tc_state,
        'other_state':other_state,
        'time_range': get_time_range(tc)
        }
    html_string += '''
<body>
  <div class="center first">
    Time Condition: <b>{tc_state}</b><br />
    Time Range<br />{time_range}<br />
    What would you like to do?<br />
    <button class="left" onclick="edit_time();">Change Time</button>
    <button class="left" onclick="change_state();" >Turn {other_state}</button>
    <button><a href="Key:Applications">Close</a></button>
  </div>
</body>'''.format(**string_template)
    return html_string

def get_time_edit_page(tc):
    html_string = '''\
<head>
{style}
  <script type="text/javascript">

'''.format(style=STYLE)

    html_string += '''\
    function get_chosen(elem_id) {
      elem = document.getElementById(elem_id);
      return elem.options.item(elem.selectedIndex).value;
    }
'''


    string_template = {'user':USER_EXT, 'pwd':USER_PWD, 'tc':tc}
    url_part = 'time_submit?user={user}&pwd={pwd}&tc={tc}&time_range='.format(**string_template)
    url_whole = os.path.join(BASE_URL_DIRECTORY, url_part)
    html_string += '''
    function submit() {{
      url_part = "{url}";
      hour_from = get_chosen("hour_from");
      min_from = get_chosen("min_from");
      hour_to = get_chosen("hour_to");
      min_to = get_chosen("min_to");
      day_week_from = get_chosen("day_week_from");
      day_week_to = get_chosen("day_week_to");
      day_month_from = get_chosen("day_month_from");
      day_month_to = get_chosen("day_month_to");
      month_from = get_chosen("month_from");
      month_to = get_chosen("month_to");

      if (hour_from == "*" || min_from == "*" || hour_to == "*" || min_to == "*") {{
        hours = "*";
      }} else {{
        hours = hour_from + ":" + min_from + "-" + hour_to + ":" + min_to;
      }}

      if (day_week_from == "*" || day_week_to == "*") {{
        days_week = "*";
      }} else {{
        days_week = day_week_from + "-" + day_week_to
      }}

      if (day_month_from == "*" || day_month_to == "*") {{
        days_month = "*";
      }} else {{
        days_month = day_month_from + "-" + day_month_to
      }}

      if (month_from == "*" || month_to == "*") {{
        months = "*";
      }} else {{
        months = month_from + "-" + month_to
      }}

      time_range = hours + "|" + days_week + "|" + days_month + "|" + months
      document.getElementById("main").innerHTML = "<div class='center first message'> Applying Changes.<br />This can take a minute...</div>";
      window.open("{url}" + time_range, "_self");
    }}
'''.format(url=url_whole)
    html_string += '''
  </script>
</head>
'''

    time_range = get_time_range(tc)
    time_dict = get_time_dict(time_range)
    html_string += '''\
<body>
  <div id="main">
  <div class="select_group">
{select_group}
  </div>
  <div class="center up">
    <button class="left" onclick="submit();">Submit</button>
    <button><a href="Key:Applications">Close</a></button>
  </div>
  </div>
</body>
'''.format(select_group=get_select_group(time_dict))

    return html_string

def get_success_page(message, tc):
    url_string_template = {
      'user': USER_EXT,
      'pwd': USER_PWD,
      'tc': tc,
    }
    string_template = {
      'style': STYLE,
      'url': BASE_URL_DIRECTORY + '?user={user}&pwd={pwd}&tc={tc}'.format(**url_string_template),
      'message': message,
    }
    html_string = '''\
<head>
{style}
</head>
<body>
  <div class="center first message">
    {message}<br />
    <button class="left"><a href="{url}">Return</a></button>
    <button><a href="Key:Applications">Close</a></button>
  </div>
</body>
'''.format(**string_template)
    return html_string

def validate_time_range(time_range):
    import re
    m = r'^(\*|[012]\d:[0-5]\d-[012]\d:[0-5]\d)\|(\*|(mon|tue|wed|thu|fri|sat|sun)-(mon|tue|wed|thu|fri|sat|sun))\|(\*|[1-3]?\d-[1-3]?\d)\|(\*|(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)-(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))$'
    return re.match(m, time_range)

def get_time_range(tc):
    try:
        int(tc)
    except ValueError:
        return 'Bad Request For Time Range'
    db = mysql.connect(host=MYSQL_HOST,
                       user=MYSQL_USER,
                       passwd=MYSQL_PASS,
                       db=MYSQL_DB)

    db_cursor = db.cursor()
    sql_query_string = 'SELECT time FROM timeconditions WHERE timeconditions_id=%s'
    db_cursor.execute(sql_query_string, (tc,))
    try:
        timegroup_id = db_cursor.fetchone()[0]
    except IndexError:
        return 'Bad Request For Time Range'
    sql_query_string = 'SELECT time FROM timegroups_details WHERE timegroupid=%s'
    db_cursor.execute(sql_query_string, (timegroup_id,))
    time_range = db_cursor.fetchone()[0]
    db.close()
    return time_range

def set_time_range(tc, time_range):
    try:
        int(tc)
    except ValueError:
        return

    if not validate_time_range(time_range):
        return

    db = mysql.connect(host=MYSQL_HOST,
                       user=MYSQL_USER,
                       passwd=MYSQL_PASS,
                       db=MYSQL_DB)

    db_cursor = db.cursor()
    sql_query_string = 'SELECT time FROM timeconditions WHERE timeconditions_id=%s'
    db_cursor.execute(sql_query_string, (tc,))
    try:
        timegroup_id = db_cursor.fetchone()[0]
    except IndexError:
        return 'Bad Request For Time Range'
    sql_query_string = 'UPDATE timegroups_details SET time=%s WHERE timegroupid=%s'
    db_cursor.execute(sql_query_string, (time_range, timegroup_id))
    db.commit()
    db.close()
    return_code = call(FREEPBX_RELOAD_ARGS)
    if return_code != 0:
        return
    return True

def get_time_dict(time_range):
    time_list = time_range.split('|')
    hours = time_list[0].split('-')
    if len(hours) > 1:
        hours_from = hours[0].split(':')
        hour_from = hours_from[0]
        min_from = hours_from[1]
        hours_to = hours[1].split(':')
        hour_to = hours_to[0]
        min_to = hours_to[1]
    else:
        hour_from = min_from = hour_to = min_to = '*'

    days_week = time_list[1].split('-')
    if len(days_week) > 1:
        day_week_from = days_week[0]
        day_week_to = days_week[1]
    else:
        day_week_from = day_week_to = '*'

    days_month = time_list[2].split('-')
    if len(days_month) > 1:
        day_month_from = days_month[0]
        day_month_to = days_month[1]
    else:
        day_month_from = day_month_to = '*'

    months = time_list[3].split('-')
    if len(months) > 1:
        month_from = months[0]
        month_to = months[1]
    else:
        month_from = month_to = '*'

    time_dict = {
        'hour_from':hour_from,
        'min_from':min_from,
        'hour_to':hour_to,
        'min_to':min_to,
        'day_week_from':day_week_from,
        'day_week_to':day_week_to,
        'day_month_from':day_month_from,
        'day_month_to':day_month_to,
        'month_from':month_from,
        'month_to':month_to,
    }
    return time_dict

def get_select_group(time_dict):
    hour_list = ['*']
    for i in range(24):
        num_string = str(i)
        if i < 10:
            num_string = '0' + num_string
        hour_list.append(num_string)

    min_list = ['*']
    for i in range(60):
        num_string = str(i)
        if i < 10:
            num_string = '0' + num_string
        min_list.append(num_string)

    day_month_list = ['*']
    for i in range(31):
        num_string = str(i + 1)
        day_month_list.append(num_string)

    day_week_list = ['*', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    month_list = ['*', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

    def make_options(item_list, match):
        option_block_string = ''
        for item in item_list:
            if item == match:
                option_string = '      <option value="{item}" selected>{item}</option>\n'.format(item=item)
            else:
                option_string = '      <option value="{item}">{item}</option>\n'.format(item=item)
            option_block_string += option_string
        return option_block_string
       
    html_string = '    Hours: \n    <select id="hour_from">\n'
    html_string += make_options(hour_list, time_dict['hour_from'])
    html_string += '    </select>\n    <select id="min_from">\n'
    html_string += make_options(min_list, time_dict['min_from'])
    html_string += '    </select>\n-\n    <select id="hour_to">\n'
    html_string += make_options(hour_list, time_dict['hour_to'])
    html_string += '    </select>\n    <select id="min_to">\n'
    html_string += make_options(min_list, time_dict['min_to'])
    html_string += '    </select><br /><br />\n\n    <span class="small">Days of the Week:</span> \n      <select id="day_week_from">\n'
    html_string += make_options(day_week_list, time_dict['day_week_from'])
    html_string += '    </select>\n-\n    <select id="day_week_to">\n'
    html_string += make_options(day_week_list, time_dict['day_week_to'])
    html_string += '    </select><br /><br />\n    <span class="small">Days of the Month:</span> \n      <select id="day_month_from">\n'
    html_string += make_options(day_month_list, time_dict['day_month_from'])
    html_string += '    </select>\n-\n    <select id="day_month_to">\n'
    html_string += make_options(day_month_list, time_dict['day_month_to'])
    html_string += '    </select><br /><br />\n    Months: \n      <select id="month_from">\n'
    html_string += make_options(month_list, time_dict['month_from'])
    html_string += '    </select>\n-\n    <select id="month_to">\n'
    html_string += make_options(month_list, time_dict['month_to'])
    html_string += '    </select>\n'

    return html_string

def application(environ, start_response):
    status_OK = '200 OK'
    status_Forbidden = '403 Forbidden'
    status_Not_Found = '404 Not Found'

    response_header = [('Content-type', 'text/html')]

    global BASE_URL_DIRECTORY
    BASE_URL_DIRECTORY = environ.get('SCRIPT_NAME','')
    path_info = environ.get('PATH_INFO', '')
    query_string = environ.get('QUERY_STRING', '')
    parsed_query = parse_qs(query_string, True)

    status = status_OK
    html_string = ''
    if path_info == '':
        if 'user' not in parsed_query \
          or 'pwd' not in parsed_query \
          or 'tc' not in parsed_query \
          or parsed_query['user'][0] != USER_EXT \
          or parsed_query['pwd'][0] != USER_PWD:
            status = status_Forbidden
            html_string = '<h1 style="text-align:center;">Denied!!!</h1>'
        else:
            tc = parsed_query['tc'][0]
            html_string = get_index(tc)

    elif path_info == '/toggle_state':
        if 'user' not in parsed_query \
          or 'pwd' not in parsed_query \
          or 'tc' not in parsed_query \
          or 'other_state' not in parsed_query \
          or parsed_query['user'][0] != USER_EXT \
          or parsed_query['pwd'][0] != USER_PWD:
            status = status_Forbidden
            html_string = '<h1 style="text-align:center;">Denied!!!</h1>'
        else:
            tc = parsed_query['tc'][0]
            other_state = parsed_query['other_state'][0]
            value = 'false_sticky'
            if other_state == 'On':
                value = ''
            db_put_return = set_db_value(tc, value)
            if db_put_return is None:
                html_string = '<h1 style="text-align:center;">Problem Changing Time Condition!</h1>'
            else:
                html_string = get_success_page('Time Condition is now {0}'.format(other_state), tc)

    elif path_info == '/time_edit':
        if 'user' not in parsed_query \
          or 'pwd' not in parsed_query \
          or 'tc' not in parsed_query \
          or parsed_query['user'][0] != USER_EXT \
          or parsed_query['pwd'][0] != USER_PWD:
            status = status_Forbidden
            html_string = '<h1 style="text-align:center;">Denied!!!</h1>'
        else:
            tc = parsed_query['tc'][0]
            html_string = get_time_edit_page(tc)

    elif path_info == '/time_submit':
        if 'user' not in parsed_query \
          or 'pwd' not in parsed_query \
          or 'tc' not in parsed_query \
          or 'time_range' not in parsed_query \
          or parsed_query['user'][0] != USER_EXT \
          or parsed_query['pwd'][0] != USER_PWD:
            status = status_Forbidden
            html_string = '<h1 style="text-align:center;">Denied!!!</h1>'
        else:
            time_range = parsed_query['time_range'][0]
            tc = parsed_query['tc'][0]
            set_time_range_result = set_time_range(tc, time_range)
            if set_time_range_result is None:
                html_string = '<h1 style="text-align:center;">Problem Changing Time Condition!</h1>'
            else:
                html_string = get_success_page('Time Range is now:<br />{0}'.format(time_range), tc)

    else:
        status = status_Not_Found
        html_string = 'Page Not Found'

    start_response(status, response_header)
    return [html_string]

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    srv = make_server('localhost', 8080, application)
    srv.serve_forever()
