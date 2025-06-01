import os, argparse, json, gettext
import pandas as pd
from msTools import i18n
from msTools.data_manager import DataManager
from msGait.movement_detector import MovementDetector
from datetime import datetime, timedelta

class VAction(argparse.Action):
    """
    Clase para manejar el nivel de verbose (-v).
    """
    def __call__(self, parser, namespace, values, option_string=None):
        if values is None:
            setattr(namespace, self.dest, getattr(namespace, self.dest) + 1)
        else:
            setattr(namespace, self.dest, int(values))

# Define the language
# idioma_app = os.environ.get('LANG', 'es') # Ex: Get it from the Environment
i18n.init_translation('es') # Inicializa la traducción

def main():
    #
    parser= argparse.ArgumentParser(description=i18n._("ARG_TIT_FIND_GAIT"))
    parser.add_argument("-i", "--ids", dest="act_all_ids", type=json.loads, required=True,
                        help=i18n._("ARG_LIST_ACT_ALL_IDS"))
    parser.add_argument("-c", "--config", dest="config_file", type=str, required=True,
                        help=i18n._("ARG_STR_PATH_YAML"))
    parser.add_argument("-l", "--lang", dest="lng", type=str, help=i18n._("ARG_STR_LNG"))
    parser.add_argument("-o","--output", dest="fout", type=str, help=i18n._("ARG-STR-FOUT-XLSX"))
    parser.add_argument("-v", "--verbose", action=VAction, nargs="?", default=0, const=1,
                        help=i18n._("ARG_VB_LEVEL"))
    args  = parser.parse_args()

    # Activity_all Management.
    if len(args.lng) > 0:
        i18n.init_translation(args.lng)

    act_all_ids = args.act_all_ids
    if args.verbose >= 1:
        print(i18n._("PRCS_LIST_ACT_ALL_IDS"))

    # Load activity windows
    data_manager = DataManager(config_path=args.config_file)
    ids_string = ', '.join(map(str, act_all_ids))
    query = f"""
        SELECT id, start_time, end_time, duration, codeid_ids, codeleg_ids, active_legs
               FROM activity_all
               WHERE id in ({ids_string}) ORDER BY codeid_ids;
    """
    try:
        activity_all = data_manager.fetch_data(query)
    except Exception as e:
        print(i18n._("FGAIT_PGSQL_ERR".format(e=e)))
        return

    if activity_all.empty:
        print(i18n._("FGAIT_NO_WINS"))
        return

    df_legs = data_manager.recover_activity_all(activity_all,args.verbose)

    # Detect effective walks
    detector = MovementDetector(data_manager=data_manager,
        sampling_rate=50, sect='movement', verbose=args.verbose)

    if args.verbose >= 1:
        print(i18n._("FGAIT_1ST"))

    fout = None
    if len(args.fout) > 0:
        fout = args.fout
    df_effective = detector.detect_effective_movement(df_legs, fout, args.verbose)

    if df_effective.empty:
        print(i18n._("FGAIT_NO_WALK"))
        return

    if args.verbose >= 2:
        print(i18n._("FGAIT_WKLS_FND"))
        print(df_effective.head())

    # Store in the Database
    detector.save_to_postgresql("effective_movement", df_effective)

    if args.verbose >= 1:
        print(i18n._("FGAIT_NUM_WALKS").format(ns=len(df_effective)))
        print(i18n._("FGAIT_END"))


if __name__ == "__main__":
    main()
