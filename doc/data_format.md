# Flysight Data Format
## Flysight V1
### File Structure
The Flysight V1 hardware revision outputs a single CSV file containing GPS track information. Flight logs are grouped into a directory by GPS date, and each flight session CSV is named based on the initial GPS time.

```
.
└── 24-04-20/
    └── 04-20-00.CSV
```

### Data Structure
```
time,lat,lon,hMSL,velN,velE,velD,hAcc,vAcc,sAcc,heading,cAcc,gpsFix,numSV
,(deg),(deg),(m),(m/s),(m/s),(m/s),(m),(m),(m/s),(deg),(deg),,
2021-04-20T04:20:00.00Z,33.6568828,-117.7466357,15.060,-0.63,0.98,0.29,207.635,481.468,7.15,0.00000,180.00000,3,4
```

The track file CSV contains 2 header lines, one with column name and one with data units, followed by one or more rows of track data.

## Flysight V2
### File Structure
The Flysight V2 hardware revision outputs a collection of files containing flight log information. Flight logs are grouped into directories by GPS date, then GPS time, based on the initial GPS time.

```
.
└── 24-04-20/
    └── 04-20-00/
        ├── RAW.UBX
        ├── SENSOR.CSV
        └── TRACK.CSV
```

Currently output files are:
  * `RAW.UBX` - The raw binary data stream from the onboard u-blox hardware; the protocol used has not been investigated
  * `SENSOR.CSV` - Data records from the onboard sensors (minus GPS)
  * `TRACK.CSV` - Data records from the GPS sensor

### Data Structure
Both the sensor and track data CSV files share a similar format: a series of header lines, followed by a delimiter (`$DATA`), and then one or more rows of data records.

Currently encountered information contained in the header file is as follows:
  * `$FLYS` - Unsure what this is :)
  * `$VAR` - Device information
  * Sensor information is provided as one or more pairs of rows:
    * `$COL` - Sensor ID & measured quantities; the sensor ID is used in the first column of a data row to identify the information source for each row
    * `$UNIT` - Measured quantity units

#### Sensor data
The sensor data stream is comingled, where the source sensor for each row is provided in the first column of each row & corresponds to the sensor information provided in the file's header.

I believe the timestamps are provided as GPS time of day, in seconds.

```
$FLYS,1
$VAR,FIRMWARE_VER,v2024.05.25.pairing_request
$VAR,DEVICE_ID,abc123
$VAR,SESSION_ID,abc123
$COL,BARO,time,pressure,temperature
$UNIT,BARO,s,Pa,deg C
$COL,HUM,time,humidity,temperature
$UNIT,HUM,s,percent,deg C
$COL,MAG,time,x,y,z,temperature
$UNIT,MAG,s,gauss,gauss,gauss,deg C
$COL,IMU,time,wx,wy,wz,ax,ay,az,temperature
$UNIT,IMU,s,deg/s,deg/s,deg/s,g,g,g,deg C
$COL,TIME,time,tow,week
$UNIT,TIME,s,s,
$COL,VBAT,time,voltage
$UNIT,VBAT,s,volt
$DATA
$IMU,59970.376,-0.427,1.770,1.953,-0.01464,-0.00732,0.94287,25.64
```

Currently seen sensors are:
  * `$BARO`
    * Time
    * Pressure
    * Temperature
  * `$HUM`
    * Time
    * Humidity
    * Temperature
  * `$IMU`
    * Time
    * Gyro XYZ
    * Accel XYC
    * Temperature
  * `$MAG`
    * Time
    * Magnetic field XYZ
  * `$TIME`
    * Time
    * Time of week
    * Week
  * `$VBAT`
    * Time
    * Voltage

#### Track data

```
$FLYS,1
$VAR,FIRMWARE_VER,v2024.05.25.pairing_request
$VAR,DEVICE_ID,abc123
$VAR,SESSION_ID,abc123
$COL,GNSS,time,lat,lon,hMSL,velN,velE,velD,hAcc,vAcc,sAcc,numSV
$UNIT,GNSS,,deg,deg,m,m/s,m/s,m/s,m,m,m/s,
$DATA
$GNSS,2024-04-20T04:20:00.000Z,33.6568828,-117.7466357,630.077,-31.92,48.42,-34.93,136.117,170.718,4.74,4
```

Currently seen sensors are:
  * `$GNSS`
    * Time (ISO format)
    * Lat
    * Lon
    * Altitude MSL
    * Northing velocity
    * Easting velocity
    * Vertical velocity
    * Horzontal accuracy
    * Vertical accuracy
    * Speed accuracy
    * Satellites in view
