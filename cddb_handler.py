import requests
from typing import Dict, List


class CDDBHandler:
    def __init__(self):
        self.base_url = "http://gnudb.gnudb.org/~cddb/cddb.cgi"
        self.client_name = "DigitalCDPlayer"
        self.client_version = "1.0"
        self.user_email = "uremail@gmail.com"
        self.disc_info = None
        self.track_info = {}

    def _build_request_url(self, command: str, **params) -> str:
        """构建 GnuDB 的查询 URL"""
        hello_str = f"{self.user_email}+my.host.com+{self.client_name}+{self.client_version}"
        proto = "6"
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.base_url}?cmd={command}&hello={hello_str}&proto={proto}&{param_str}"

    def get_cd_info(self, disc_id: str, num_tracks: int, track_offsets: List[int], total_length: int) -> Dict:
        """获取 CD 信息"""
        try:
            # 构造查询命令
            offsets = "+".join(map(str, track_offsets))
            command = f"cddb+query+{disc_id}+{num_tracks}+{offsets}+{total_length}"
            url = self._build_request_url(command=command)

            # 发送请求
            response = requests.get(url)
            response.raise_for_status()

            # 解析返回结果
            result_lines = response.text.splitlines()
            if result_lines[0].startswith("200"):
                self.disc_info = self._parse_cd_info(result_lines)
                return self.disc_info
            else:
                print(f"CDDB 查询失败: {result_lines[0]}")
                return {}
        except Exception as e:
            print(f"获取 CD 信息失败: {e}")
            return {}

    def _parse_cd_info(self, result_lines: List[str]) -> Dict:
        """解析 CD 信息返回值"""
        cd_info = {}
        first_line = result_lines[1]
        parts = first_line.split(" / ")
        if len(parts) >= 2:
            cd_info["album"] = parts[1]
            cd_info["artist"] = parts[0]

        # 解析音轨信息
        tracks = []
        for line in result_lines[2:]:
            if line.startswith("TTITLE"):
                track_number, title = line.split("=", 1)
                track_number = int(track_number.replace("TTITLE", ""))
                tracks.append({"number": track_number + 1, "title": title.strip()})
        cd_info["tracks"] = tracks
        return cd_info

    def get_track_info(self, track_number: int) -> Dict:
        """获取指定音轨信息"""
        return self.track_info.get(track_number, {
            "number": str(track_number),
            "title": f"Track {track_number}",
        })


# 示例调用
if __name__ == "__main__":
    handler = CDDBHandler()
    disc_id = "9a09340d"  # 示例 Disc ID
    num_tracks = 10
    track_offsets = [150, 30000, 60000, 90000]  # 示例偏移量
    total_length = 120000

    cd_info = handler.get_cd_info(disc_id, num_tracks, track_offsets, total_length)
    if cd_info:
        print("CD Info:", cd_info)
