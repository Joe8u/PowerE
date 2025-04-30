import os
import pandas as pd

RAW_CSV = os.path.join('data','raw','lastprofile',
                       'Swiss_load_curves_2015_2035_2050.csv')
BASE_OUT = os.path.join('data','processed','lastprofile')
YEARS = [2015, 2035, 2050]

def preprocess_lastprofile():
    df = pd.read_csv(RAW_CSV, sep=';', parse_dates=['Time'])
    df.rename(columns={
        'Year':'year','Month':'month','Appliances':'appliance',
        'Day type':'day_type','Time':'time','Power (MW)':'power_mw'
    }, inplace=True)

    for year in YEARS:
        df_year = df[df['year']==year]
        if df_year.empty: continue

        out_year_dir = os.path.join(BASE_OUT,str(year))
        for appliance in df_year['appliance'].unique():
            for dt in df_year['day_type'].unique():
                df_sub = df_year[
                   (df_year['appliance']==appliance)&
                   (df_year['day_type']==dt)
                ].copy()
                df_sub.set_index('time', inplace=True)

                folder = os.path.join(out_year_dir,
                                      appliance.replace(' ','_'),
                                      dt)
                os.makedirs(folder, exist_ok=True)

                # Monats-Parquets
                for m in range(1,13):
                    df_month = df_sub[df_sub.index.month==m]
                    if df_month.empty: continue
                    target = os.path.join(folder,f'month_{m:02d}.parquet')
                    df_month.to_parquet(target)

                # Tages-Durchschnitt nur für power_mw
                df_daily = df_sub['power_mw'].resample('D').mean().to_frame()
                daily_target = os.path.join(
                    folder,  # tägliche Dateien in selbem Appliance/day_type-Ordner
                    f'daily_average_{dt}.parquet'
                )
                df_daily.to_parquet(daily_target)

        print(f"Finished preprocessing for {year}")

    print("All done.")