#
# [NetworkConfig]
#
# DEBUG > INFO > WARNING > ERROR > CRITICAL
class DataNetwork5GConfig:
    PLMN_HOME = "00101"
    PLMN_ROAMING = "99970"
    PLMN_LIST_ALLOWED = ["00101", "99970"]
    APN = "internet"
    IP_TYPE = "ipv4"