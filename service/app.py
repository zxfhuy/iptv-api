import os
import sys

sys.path.append(os.path.dirname(sys.path[0]))
from flask import Flask, send_from_directory, make_response, jsonify, redirect
from utils.tools import get_result_file_content, get_ip_address, resource_path
from utils.config import config
import utils.constants as constants
from utils.db import get_db_connection, return_db_connection
import subprocess
import atexit
from collections import OrderedDict
import threading
import json

app = Flask(__name__)
nginx_dir = resource_path(os.path.join('utils', 'nginx-rtmp-win32'))
nginx_path = resource_path(os.path.join(nginx_dir, 'nginx.exe'))
stop_path = resource_path(os.path.join(nginx_dir, 'stop.bat'))
hls_temp_path = resource_path(os.path.join(nginx_dir, 'temp/hls')) if sys.platform == "win32" else '/tmp/hls'
os.makedirs(f"{constants.output_dir}/data", exist_ok=True)

live_running_streams = OrderedDict()
hls_running_streams = OrderedDict()
MAX_STREAMS = 10


@app.route("/")
def show_index():
    return get_result_file_content(
        path=constants.live_result_path if config.open_rtmp else config.final_file,
        file_type="m3u" if config.open_m3u_result else "txt"
    )


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(resource_path('static/images'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


@app.route("/txt")
def show_txt():
    return get_result_file_content(path=config.final_file, file_type="txt")


@app.route("/ipv4/txt")
def show_ipv4_txt():
    return get_result_file_content(path=constants.ipv4_result_path, file_type="txt")


@app.route("/ipv6/txt")
def show_ipv6_txt():
    return get_result_file_content(path=constants.ipv6_result_path, file_type="txt")


@app.route("/live")
def show_live():
    return get_result_file_content(path=constants.live_result_path,
                                   file_type="m3u" if config.open_m3u_result else "txt")


@app.route("/live/txt")
def show_live_txt():
    return get_result_file_content(path=constants.live_result_path, file_type="txt")


@app.route("/live/ipv4/txt")
def show_live_ipv4_txt():
    return get_result_file_content(path=constants.live_ipv4_result_path, file_type="txt")


@app.route("/live/ipv6/txt")
def show_live_ipv6_txt():
    return get_result_file_content(path=constants.live_ipv6_result_path, file_type="txt")


@app.route("/hls")
def show_hls():
    return get_result_file_content(path=constants.hls_result_path,
                                   file_type="m3u" if config.open_m3u_result else "txt")


@app.route("/hls/txt")
def show_hls_txt():
    return get_result_file_content(path=constants.hls_result_path, file_type="txt")


@app.route("/hls/ipv4/txt")
def show_hls_ipv4_txt():
    return get_result_file_content(path=constants.hls_ipv4_result_path, file_type="txt")


@app.route("/hls/ipv6/txt")
def show_hls_ipv6_txt():
    return get_result_file_content(path=constants.hls_ipv6_result_path, file_type="txt")


@app.route("/m3u")
def show_m3u():
    return get_result_file_content(path=config.final_file, file_type="m3u")


@app.route("/live/m3u")
def show_live_m3u():
    return get_result_file_content(path=constants.live_result_path, file_type="m3u")


@app.route("/hls/m3u")
def show_hls_m3u():
    return get_result_file_content(path=constants.hls_result_path, file_type="m3u")


@app.route("/ipv4/m3u")
def show_ipv4_m3u():
    return get_result_file_content(path=constants.ipv4_result_path, file_type="m3u")


@app.route("/ipv4")
def show_ipv4_result():
    return get_result_file_content(
        path=constants.live_ipv4_result_path if config.open_rtmp else constants.ipv4_result_path,
        file_type="m3u" if config.open_m3u_result else "txt"
    )


@app.route("/ipv6/m3u")
def show_ipv6_m3u():
    return get_result_file_content(path=constants.ipv6_result_path, file_type="m3u")


@app.route("/ipv6")
def show_ipv6_result():
    return get_result_file_content(
        path=constants.live_ipv6_result_path if config.open_rtmp else constants.ipv6_result_path,
        file_type="m3u" if config.open_m3u_result else "txt"
    )


@app.route("/live/ipv4/m3u")
def show_live_ipv4_m3u():
    return get_result_file_content(path=constants.live_ipv4_result_path, file_type="m3u")


@app.route("/live/ipv6/m3u")
def show_live_ipv6_m3u():
    return get_result_file_content(path=constants.live_ipv6_result_path, file_type="m3u")


@app.route("/hls/ipv4/m3u")
def show_hls_ipv4_m3u():
    return get_result_file_content(path=constants.hls_ipv4_result_path, file_type="m3u")


@app.route("/hls/ipv6/m3u")
def show_hls_ipv6_m3u():
    return get_result_file_content(path=constants.hls_ipv6_result_path, file_type="m3u")


@app.route("/content")
def show_content():
    return get_result_file_content(
        path=constants.live_result_path if config.open_rtmp else config.final_file,
        file_type="m3u" if config.open_m3u_result else "txt",
        show_content=True
    )


@app.route("/epg/epg.xml")
def show_epg():
    return get_result_file_content(path=constants.epg_result_path, show_content=False)


@app.route("/epg/epg.gz")
def show_epg_gz():
    return get_result_file_content(path=constants.epg_gz_result_path, show_content=False)


@app.route("/log")
def show_log():
    if os.path.exists(constants.sort_log_path):
        with open(constants.sort_log_path, "r", encoding="utf-8") as file:
            content = file.read()
    else:
        content = constants.waiting_tip
    response = make_response(content)
    response.mimetype = "text/plain"
    return response


def get_channel_data(channel_id):
    conn = get_db_connection(constants.rtmp_data_path)
    channel_data = {}
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT url, headers FROM result_data WHERE id=?", (channel_id,))
        data = cursor.fetchone()
        if data:
            channel_data = {
                'url': data[0],
                'headers': json.loads(data[1]) if data[1] else None
            }
    except Exception as e:
        print(f"❌ Error retrieving channel data: {e}")
    finally:
        return_db_connection(constants.rtmp_data_path, conn)
    return channel_data


def monitor_stream_process(streams, process, channel_id):
    process.wait()
    if channel_id in streams:
        del streams[channel_id]


def cleanup_streams(streams):
    to_delete = []
    for channel_id, process in streams.items():
        if process.poll() is not None:
            to_delete.append(channel_id)
    for channel_id in to_delete:
        del streams[channel_id]
    while len(streams) > MAX_STREAMS:
        streams.popitem(last=False)


@app.route('/live/<channel_id>', methods=['GET'])
def run_live(channel_id):
    if not channel_id:
        return jsonify({'Error': 'Channel ID is required'}), 400
    data = get_channel_data(channel_id)
    url = data.get("url", "")
    if not url:
        return jsonify({'Error': 'Url not found'}), 400
    headers = data.get("headers", None)
    if channel_id in live_running_streams:
        process = live_running_streams[channel_id]
        if process.poll() is None:
            return redirect(f'rtmp://localhost:1935/live/{channel_id}')
        else:
            del live_running_streams[channel_id]
    cleanup_streams(live_running_streams)
    cmd = [
        'ffmpeg',
        '-loglevel', 'error',
        '-re',
        '-headers', ''.join(f'{k}: {v}\r\n' for k, v in headers.items()) if headers else '',
        '-i', url.partition('$')[0],
        '-c:v', 'copy',
        '-c:a', 'copy',
        '-f', 'flv',
        '-flvflags', 'no_duration_filesize',
        f'rtmp://localhost:1935/live/{channel_id}'
    ]
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE
        )
        threading.Thread(
            target=monitor_stream_process,
            args=(live_running_streams, process, channel_id),
            daemon=True
        ).start()
        live_running_streams[channel_id] = process
        return redirect(f'rtmp://localhost:1935/live/{channel_id}')
    except Exception as e:
        return jsonify({'Error': str(e)}), 500


@app.route('/hls/<channel_id>', methods=['GET'])
def run_hls(channel_id):
    if not channel_id:
        return jsonify({'Error': 'Channel ID is required'}), 400
    data = get_channel_data(channel_id)
    url = data.get("url", "")
    if not url:
        return jsonify({'Error': 'Url not found'}), 400
    headers = data.get("headers", None)
    channel_file = f'{channel_id}.m3u8'
    m3u8_path = os.path.join(hls_temp_path, channel_file)
    if channel_id in hls_running_streams:
        process = hls_running_streams[channel_id]
        if process.poll() is None:
            if os.path.exists(m3u8_path):
                return redirect(f'http://localhost:8080/hls/{channel_file}')
            else:
                return jsonify({'status': 'pending', 'message': 'Stream is starting'}), 202
        else:
            del hls_running_streams[channel_id]
    cleanup_streams(hls_running_streams)
    cmd = [
        'ffmpeg',
        '-loglevel', 'error',
        '-re',
        '-headers', ''.join(f'{k}: {v}\r\n' for k, v in headers.items()) if headers else '',
        '-stream_loop', '-1',
        '-i', url.partition('$')[0],
        '-c:v', 'copy',
        '-c:a', 'copy',
        '-f', 'flv',
        '-flvflags', 'no_duration_filesize',
        f'rtmp://localhost:1935/hls/{channel_id}'
    ]
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE
        )
        threading.Thread(
            target=monitor_stream_process,
            args=(hls_running_streams, process, channel_id),
            daemon=True
        ).start()
        hls_running_streams[channel_id] = process
        return jsonify({
            'status': 'starting',
            'message': 'Stream is being prepared'
        }), 202
    except Exception as e:
        return jsonify({'Error': str(e)}), 500


def stop_rtmp_service():
    if sys.platform == "win32":
        try:
            os.chdir(nginx_dir)
            subprocess.Popen([stop_path], shell=True)
        except Exception as e:
            print(f"❌ Rtmp service stop failed: {e}")


def run_service():
    try:
        if not os.getenv("GITHUB_ACTIONS"):
            if config.open_rtmp and sys.platform == "win32":
                original_dir = os.getcwd()
                try:
                    os.chdir(nginx_dir)
                    subprocess.Popen([nginx_path], shell=True)
                except Exception as e:
                    print(f"❌ Rtmp service start failed: {e}")
                finally:
                    os.chdir(original_dir)
            ip_address = get_ip_address()
            print(f"📄 Result content: {ip_address}/content")
            print(f"📄 Log content: {ip_address}/log")
            if config.open_m3u_result:
                print(f"🚀 M3u api: {ip_address}/m3u")
            print(f"🚀 Txt api: {ip_address}/txt")
            if config.open_rtmp:
                if config.open_m3u_result:
                    print(f"🚀 Rtmp live M3u api: {ip_address}/live/m3u")
                    print(f"🚀 Rtmp hls M3u api: {ip_address}/hls/m3u")
                print(f"🚀 Rtmp live Txt api: {ip_address}/live/txt")
                print(f"🚀 Rtmp hls Txt api: {ip_address}/hls/txt")
            print(f"🚀 IPv4 Txt api: {ip_address}/ipv4")
            print(f"🚀 IPv6 Txt api: {ip_address}/ipv6")
            print(f"✅ You can use this url to watch IPTV 📺: {ip_address}")
            app.run(host="0.0.0.0", port=config.app_port)
    except Exception as e:
        print(f"❌ Service start failed: {e}")


if __name__ == "__main__":
    if config.open_rtmp:
        atexit.register(stop_rtmp_service)
    run_service()
