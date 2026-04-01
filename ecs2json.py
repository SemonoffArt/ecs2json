#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Модуль для поиска и индексирования ECS тегов в проекте
# Версия для работы с MS Access файлами напрямую
#
import logging
from pathlib import Path
import pyodbc
import time
from alive_progress import alive_bar, config_handler
from colorama import init, Fore
from colorama import Style
import re
import yaml
import csv

# Абсолютный путь к директории с скриптом
_PRG_DIR = Path(__file__).parent.absolute()
_UTL_DIR = _PRG_DIR / 'utils'

_RES_DIR = _PRG_DIR / 'data'
_TAG_DB_DIR = _RES_DIR / 'FlsaProDb'


_PLCNAME = {0: 'spare', 1: '991', 2: '992', 3: '990'}
_PLCMEMTYP = {
    '17': '16 Bit',
    '21': '16 Bit',
    '22': '32 Bit',
    '23': 'Float',
    '26': '16 Bit/Time',
    '28': 'Float/Stat/Timer',
    '29': '8 Bit',
    '30': 'Flt/Trig/Sts',
}
logger = logging.getLogger()


class DBHelper(object):
    """ECS хранит базу тэгов в формате Ms Access,
    класс работает с файлами mdb ECS напрямую через pyodbc.
    """

    def __init__(self):
        self.sdrpoint = _TAG_DB_DIR / 'SdrPoint30.mdb'
        self.sdrapalg = _TAG_DB_DIR / 'SdrApAlg30.mdb'
        self.sdrblkalg = _TAG_DB_DIR / 'SdrBlkAlg30.mdb'
        self.sdrbpalg = _TAG_DB_DIR / 'SdrBpAlg30.mdb'
        self.sdrsims5config = _TAG_DB_DIR / 'SdrSimS5Config30.mdb'
        self.sdrpnttextdyn = _TAG_DB_DIR / 'SdrPntTextDyn30.mdb'

        if not self.sdrpoint.is_file() or not self.sdrblkalg.is_file() or not self.sdrbpalg.is_file() \
                or not self.sdrsims5config.is_file():
            raise Exception(f"Can't open db file {self.sdrpoint}")

        # Кэширование справочников для ускорения обработки
        self._blk_alg_cache = {}
        self._conv_alg_cache = {}
        self._eng_unit_cache = {}
        self._load_caches()

    @staticmethod
    def _get_connection_string(mdb_file):
        """Создает строку подключения для MS Access"""
        return (
            r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
            f'DBQ={mdb_file};'
        )

    def _sql_fetchall(self, bd, sql):
        """Выполняет SQL запрос и возвращает все строки"""
        try:
            conn_str = self._get_connection_string(bd)
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            cursor.execute(sql)
            result = cursor.fetchall()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Ошибка выполнения SQL: {e}")
            return []

    def _sql_fetchone(self, bd, sql):
        """Выполняет SQL запрос и возвращает одну строку"""
        try:
            conn_str = self._get_connection_string(bd)
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            cursor.execute(sql)
            result = cursor.fetchone()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Ошибка выполнения SQL: {e}")
            return None

    def _load_caches(self):
        """Загружает справочники в память для быстрого доступа"""
        print(f"{Fore.CYAN}Загрузка справочников в память...{Style.RESET_ALL}")
        
        # Кэш блоков алгоритмов: {AlgNo: BlockTableName}
        try:
            sql = "SELECT AlgNo, BlockTableName FROM BlockDescriptionIndex"
            result = self._sql_fetchall(self.sdrblkalg, sql)
            self._blk_alg_cache = {row.AlgNo: row.BlockTableName for row in result}
            logger.info(f"Загружено {len(self._blk_alg_cache)} записей BlockDescriptionIndex")
        except Exception as e:
            logger.error(f"Ошибка загрузки кэша BlockDescriptionIndex: {e}")

        # Кэш алгоритмов конвертации: {CaptionKey: English}
        try:
            sql = "SELECT CaptionKey, English FROM AlgMaster"
            result = self._sql_fetchall(self.sdrbpalg, sql)
            self._conv_alg_cache = {row.CaptionKey: row.English for row in result}
            logger.info(f"Загружено {len(self._conv_alg_cache)} записей AlgMaster")
        except Exception as e:
            logger.error(f"Ошибка загрузки кэша AlgMaster: {e}")

        # Кэш единиц измерения: {CaptionKey: English}
        try:
            sql = "SELECT CaptionKey, English FROM EunDef"
            result = self._sql_fetchall(self.sdrpnttextdyn, sql)
            self._eng_unit_cache = {row.CaptionKey: row.English for row in result}
            logger.info(f"Загружено {len(self._eng_unit_cache)} записей EunDef")
        except Exception as e:
            logger.error(f"Ошибка загрузки кэша EunDef: {e}")

        print(f"{Fore.GREEN}Справочники загружены{Style.RESET_ALL}")

    def get_blk_alg_name(self, alg_no=0) -> str:
        """Получает название блока алгоритма из кэша"""
        try:
            alg_no = int(alg_no) if alg_no else 0
            return self._blk_alg_cache.get(alg_no, f"{alg_no} unknown")
        except Exception as e:
            logger.error(f"Ошибка получения BlockAlg: {e}")
            return f"{alg_no} unknown"

    def get_conv_alg_name(self, alg_no=0) -> str:
        """Получает название алгоритма конвертации из кэша"""
        try:
            alg_no = int(alg_no) if alg_no else 0
            return self._conv_alg_cache.get(alg_no, f"{alg_no} unknown")
        except Exception as e:
            logger.error(f"Ошибка получения ConvAlg: {e}")
            return f"{alg_no} unknown"

    def get_eng_unit(self, caption_key) -> str:
        """Получает описание единицы измерения из кэша"""
        try:
            if not caption_key:
                return ""
            return self._eng_unit_cache.get(caption_key, "")
        except Exception as e:
            logger.error(f"Ошибка получения EngUnit: {e}")
            return ""

    def get_tag(self, tag, only_a_point=False):
        """Получает теги из базы данных с JOIN двух баз Access"""
        try:
            # Подключаемся к основной базе SdrPoint30.mdb
            conn_str = self._get_connection_string(self.sdrpoint)
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()

            # Формируем условие для фильтрации только A-точек
            sql_apoint = "PointConfig.PointId > 0 AND " if only_a_point is True else ""

            # Запрос с JOIN к внешней базе SdrSimS5Config30.mdb
            # В MS Access используется синтаксис для подключения внешних таблиц
            sim_db_path = str(self.sdrsims5config).replace('\\', '\\\\')
            
            sql = f"""
            SELECT
                PointConfig.PointId,
                PointConfig.PointCode,
                PointConfig.DefaultText,
                PointConfig.LocalText,
                PointConfig.ConvAlg,
                PointConfig.CalcAlg,
                PointConfig.BlockAlg,
                Groups.GroupCode,
                sim.PLCNo,
                sim.InputType,
                sim.InputBlock,
                sim.InputWord,
                sim.InputBit,
                sim.OutputType,
                sim.OutputBlock,
                sim.OutputWord,
                sim.OutputBit,
                sim.ParameterBlock,
                PointConfig.BlockAlg,
                PointConfig.ConvAlg,
                APointConfig.EngUnitId,
                APointConfig.Format,
                APointConfig.Constant1,
                APointConfig.SignalLow,
                APointConfig.SignalHigh,
                APointConfig.AlarmLow,
                APointConfig.AlarmHigh
            FROM
                ((PointConfig
                INNER JOIN Groups ON Groups.GroupNo = PointConfig.GroupNo)
                LEFT JOIN APointConfig ON PointConfig.PointId = APointConfig.PointId)
                INNER JOIN [;DATABASE={sim_db_path}].Points AS sim ON PointConfig.PointId = sim.SDRPointNo
            WHERE
                {sql_apoint}
                PointConfig.PointCode LIKE '%{tag}%'
            """
                # AND PointConfig.PointCode NOT LIKE '%_SPM%' 
                # AND PointConfig.PointCode NOT LIKE '%_SPA%' 
            cursor.execute(sql)
            result = cursor.fetchall()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Ошибка при получении тегов: {e}")
            print(f"{Fore.RED}ОШИБКА: {e}{Style.RESET_ALL}")
            return []


class TagsHelper(object):
    def __init__(self, tags_pattern='', with_mimic=False):
        self.db = DBHelper()
        self.tags = []
        self.tags_pattern = tags_pattern
        self.with_mimic = with_mimic
        self.only_a_point = False
        self.only_without_mimic = True
        self.cnt_files = 0  # количество обработаных файлов
        self.cnt_strings = 0  # количество обработаных строк
        self.cnt_tags = 0  # количество обработаных тэгов
        self.index_time = 0
        self.index_date = ""
        self.pages_without_tags = ""
        self.mimic_dir = _RES_DIR / 'ECS2261'
        self.update()
        logger.info(f"Init class TagsHelper")

    def __len__(self):
        return len(self.tags)

    def __getitem__(self, tag):
        for cur_tag in self.tags:
            if cur_tag['Tag'] == tag:
                return cur_tag

    def __iter__(self):
        return iter(self.tags)

    def __get__(self, instance, owner):
        return self.tags

    def update(self):
        """Обновляет список тегов из базы данных"""
        start_time = time.time()
        self.tags.clear()
        tags = []
        logger.info(f"Start update tags from MS Access DB")
        print(f"{Fore.YELLOW}Поиск тегов в базе MS Access")
        print(f"{Fore.YELLOW}Выборка из базы. Тег :{Fore.GREEN + self.tags_pattern + Style.RESET_ALL}")
        print(f"{Fore.WHITE}Только A точки: {Fore.GREEN + str(self.only_a_point) + Style.RESET_ALL}")
        print(f"{Fore.WHITE}Без SPA, SPM: {Fore.GREEN + str(True) + Style.RESET_ALL}")

        # Прямая выборка без промежуточного bar
        tags = self.db.get_tag(self.tags_pattern, self.only_a_point)
        print(f"{Fore.WHITE}Найдено тегов: {Fore.GREEN + str(len(tags)) + Style.RESET_ALL}")

        if not tags:
            self.index_time = time.time() - start_time
            logger.info(f"No tags found")
            return

        # Предварительная локализация методов для ускорения цикла
        get_conv_alg_name = self.db.get_conv_alg_name
        get_blk_alg_name = self.db.get_blk_alg_name
        get_eng_unit = self.db.get_eng_unit
        
        # Локальные ссылки на словари для скорости
        plcname_get = _PLCNAME.get
        plcmemtyp_get = _PLCMEMTYP.get

        print(f"{Fore.WHITE}Формирования словаря Тегов :{Fore.GREEN + str(len(tags)) + Style.RESET_ALL}")

        with alive_bar(len(tags), force_tty=True, length=30, title="Обработка тегов") as bar:
            for tag in tags:
                tag_data = {
                    "Id": tag[0],
                    "Tag": tag[1],
                    "Groups": tag[7],
                    "DescEng": tag[2],
                    "DescRus": str(tag[3]),
                    "Algorithms": {
                        "ConvAlg": f"{tag[4]} {get_conv_alg_name(tag[4])}",
                        "CalcAlg": tag[5],
                        "BlockAlg": f"{tag[6]} {get_blk_alg_name(tag[6])}"
                    },
                    "PLC": {
                        "PLCNo": plcname_get(tag[8]),
                        "FC": tag[17],
                        "Input": {
                            "Type": plcmemtyp_get(str(tag[9])),
                            "Block": tag[10],
                            "Word": tag[11],
                            "Bit": tag[12]
                        },
                        "Output": {
                            "Type": plcmemtyp_get(str(tag[13])),
                            "Block": tag[14],
                            "Word": tag[15],
                            "Bit": tag[16]
                        },
                    },
                    "PLC_INP": f"%DB{tag[10]}.DBD{tag[11]}",
                    "Constant1": tag[22],
                    "SignalLow": tag[23],
                    "SignalHigh": tag[24],
                    "AlarmLow": tag[25],
                    "AlarmHigh": tag[26],
                    "EngUnitId": get_eng_unit(tag[20])


                }
                self.tags.append(tag_data)
                bar()

        if self.with_mimic:
            self.find_tags_on_mimics()

        self.index_time = time.time() - start_time
        print(f"{Fore.WHITE}Обработано файлов: {Fore.GREEN + str(self.cnt_files) + Style.RESET_ALL}")
        print(f"{Fore.WHITE}За время: {Fore.GREEN + str(self.index_time) + Style.RESET_ALL}")
        logger.info(f"Update complete")

    def find_tags_on_mimics(self):
        """Поиск тегов на мнемосхемах"""
        i = 0
        self.cnt_files = 0
        mimics_in_dir = self.mimic_dir.glob('*.g')
        mimics_col = sum([1 for _ in self.mimic_dir.glob('*.g')])
        print(f"{Fore.YELLOW}Поиск тегов на мнемосхемах\r\n"
              f"{Fore.WHITE}Количество тегов: {Fore.GREEN} {len(self.tags)}{Fore.WHITE}\r\n"
              f"{Fore.WHITE}Количество мнемосхем: {Fore.GREEN} {mimics_col}{Fore.WHITE}")

        with alive_bar(len(self.tags), force_tty=True, length=30) as bar:
            for tag in self.tags:
                mimics_list = []
                for mimic in self.mimic_dir.glob('*.g'):
                    if self.find_tag_on_mimic(mimic, tag['Tag']):
                        mimics_list.append(mimic.name)
                    self.cnt_files += 1

                self.tags[i]['Mimics'] = mimics_list
                i += 1
                bar()

    def find_tag_on_mimic(self, mimic, tag) -> bool:
        """Проверяет наличие тега на мнемосхеме"""
        mim = _RES_DIR / 'ECS2261' / mimic
        if not mim.is_file():
            err_msg = f"Cannot find file: {mim} "
            logger.error(err_msg)
            raise FileNotFoundError(err_msg)
        else:
            with open(mim) as f:
                if tag in f.read():
                    return True

    def get_tags_without_mimic(self) -> list:
        """Возвращает список тегов без мнемосхем"""
        tag_wo_mim = []
        for tag in self.tags:
            if len(tag['Mimics']) == 0:
                tag_wo_mim.append(tag)

        print(f"{Fore.WHITE}Тегов без мнемомосхем:{Fore.GREEN}  {len(tag_wo_mim)}  {Style.RESET_ALL}")
        return tag_wo_mim

    @staticmethod
    def to_yaml(tags) -> str:
        return yaml.dump(tags, default_flow_style=False, indent=3, sort_keys=False, allow_unicode=True)

    def save_csv(self, tags=None):
        """Сохраняет теги в CSV файл"""
        tags = tags or self.tags
        field_names = ['Id', 'Tag', 'DescEng', 'DescRus', 'Groups', 'PLC', 'PLC_INP', 'Algorithms', 'Mimics']
        with open('tags.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=field_names)
            writer.writeheader()
            writer.writerows(tags)
        print(f"{Fore.YELLOW}Теги сохранены в:{Fore.GREEN}  tags.csv  {Style.RESET_ALL}")

    def save_yaml(self, tags=None):
        """Сохраняет теги в YAML файл"""
        tags = tags or self.tags
        tags = self.to_yaml(tags)
        with open("tags.yaml", 'w', encoding='utf-8') as target:
            target.write(tags)
        print(f"{Fore.YELLOW}Теги сохранены в :{Fore.GREEN}  tags.yaml   {Style.RESET_ALL}")

    def save_telegraf(self, tags=None):
        """Перечень OPC тегов для telegraf.conf"""
        tags = tags or self.tags
        field_names = ['Id', 'Tag', 'DescEng', 'DescRus', 'Groups', 'PLC', 'PLC_INP', 'Algorithms', 'Mimics']
        nodes = []
        tags_str = "   nodes = [\n"
        with open('tags.telegraf.conf', 'w', newline='', encoding='utf-8') as tconf:
            for tag in tags:
                tags_str += (f'     {{name="{tag["Tag"]} {tag["DescEng"]}", namespace="1", identifier_type="s", '
                             f'identifier="t|{tag["Tag"]}"}},\n')

            tags_str += "]"
            tconf.write(tags_str)

        print(f"{Fore.YELLOW}Теги сохранены в:{Fore.GREEN}  tags.telegraf.conf  {Style.RESET_ALL}")

    def save_oh_equip_json(self, tags=None):
        """Сохраняет теги в формате equips.json"""
        import json
        tags = tags or self.tags
        equips = []
        for tag in tags:
            eq_name = tag["Tag"].replace("", "")
            equip = {
                "eq_name": eq_name,
                "plc_name": tag["PLC"]["PLCNo"],
                "db_num": tag["PLC"]["Input"]["Block"],
                "db_addr": int(tag["PLC"]["Input"]["Word"] or 0) + 16,
                "description": tag["DescEng"]  # Используем DescEng из базы
            }
            equips.append(equip)
        data = {"equips": equips}
        with open(_PRG_DIR / "equips1.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"{Fore.YELLOW}Оборудование сохранено в: {Fore.GREEN}  equips1.json  {Style.RESET_ALL}")

    def save_json(self, tags=None):
        """Сохраняет теги в JSON файл"""
        import json
        tags = tags or self.tags
        with open("tags.json", "w", encoding="utf-8") as f:
            json.dump(tags, f, ensure_ascii=False, indent=4)
        print(f"{Fore.YELLOW}Теги сохранены в:{Fore.GREEN}  tags.json  {Style.RESET_ALL}")




def main():
    """Главная функция"""
    try:
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}ECS Tags to Equips (MS Access version)")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        
        tags = TagsHelper("", with_mimic=False)  #"MAINT%_MH" 
        # tags.save_oh_equip_json()
        tags.save_yaml()
        tags.save_json()
        print(f"\n{Fore.GREEN}Готово! Обработано {len(tags)} тегов.{Style.RESET_ALL}")
        # input("\nНажмите Enter для выхода...")
    except Exception as e:
        print(f"\n{Fore.RED}ОШИБКА: {e}{Style.RESET_ALL}")
        logger.error(f"Ошибка в main: {e}", exc_info=True)
        # input("\nНажмите Enter для выхода...")


if __name__ == '__main__':
    main()
