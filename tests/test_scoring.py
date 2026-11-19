import pandas as pd
import pytest
from campuspulse.scoring import calculate_indicator

def test_indicator_and_coverage():
    df=calculate_indicator(pd.DataFrame({"Name":["A","B"],"Marks":[100,50],"Attendance":[100,None]}))
    assert df.Campus_Indicator.between(0,100).all()
    assert df.loc[0,"Indicator_Coverage"] == 65
    assert df.loc[1,"Indicator_Coverage"] == 40

def test_missing_data():
    df=calculate_indicator(pd.DataFrame({"Marks":[None]}))
    assert pd.isna(df.loc[0,"Campus_Indicator"])
    assert df.loc[0,"Indicator_Band"] == "Insufficient data"

def test_bad_weights():
    with pytest.raises(ValueError): calculate_indicator(pd.DataFrame({"Marks":[50]}),{"Marks":-1})
