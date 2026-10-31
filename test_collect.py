import unittest
from collect import normalize, rows_from
class FeedTests(unittest.TestCase):
 def test_feed_native_shape(self):
  rows,err=normalize('loto6',[{'round':1,'date':'2000-10-05','numbers':[30,2,8,10,13,27],'bonus':[39]}])
  self.assertEqual(rows[0]['n1'],2); self.assertEqual(rows[0]['bonus1'],39); self.assertEqual(err,[])
 def test_camel_case_shape(self):
  rows,err=normalize('loto7',[{'drawNumber':1,'date':'2013-04-05','main':[1,3,5,7,9,11,13],'bonus':[15,17]}])
  self.assertEqual(rows[0]['bonus2'],17); self.assertEqual(err,[])
 def test_numbers_leading_zero(self):
  rows,err=normalize('numbers3',[{'round':1,'date':'2020-01-01','numbers':'007'}])
  self.assertEqual(rows[0]['winning_number'],'007'); self.assertEqual(err,[])
 def test_numbers_excel_text(self):
  rows,err=normalize('numbers4',[{'round':1,'date':'2020-01-01','numbers':'="0171"'}])
  self.assertEqual(rows[0]['winning_number'],'0171'); self.assertEqual(err,[])
 def test_bingo5_order_and_column_validation(self):
  vals=[5,10,15,20,25,30,35,40]
  rows,err=normalize('bingo5',[{'round':1,'date':'2017-04-05','numbers':vals}])
  self.assertEqual([rows[0][f'n{i}'] for i in range(1,9)],vals); self.assertEqual(err,[])
  rows,err=normalize('bingo5',[{'round':2,'date':'2017-04-12','numbers':[6,10,15,20,25,30,35,40]}])
  self.assertTrue(err)
 def test_invalid_row_is_reported(self):
  rows,err=normalize('miniloto',[{'round':1,'date':'x','numbers':[1,2,2,4,5],'bonus':[6]}])
  self.assertEqual(rows,[]); self.assertTrue(err)
 def test_wrapped_rows(self):
  self.assertEqual(rows_from({'data':[{'round':1}]}),[{'round':1}])
 def test_draws_wrapped_rows(self):
  self.assertEqual(rows_from({'draws':[{'drawNumber':1}]}),[{'drawNumber':1}])
if __name__=='__main__': unittest.main()
