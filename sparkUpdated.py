"""# Import libraries"""
import pyspark.sql.functions as f
from pyspark.sql import SparkSession
import pyspark
from pyspark import StorageLevel


"""# Read The Dataset"""
#TODO(Done): Read about spark local Vs cluster mode
#TODO(Done): Read about spark session Vs spark context: Spark session includes spark context and sql context and others
spark = SparkSession.builder.master("spark://192.168.56.1:7077").appName("SparkTaskWithCaching").config("spark.some.config.option", "some-value").getOrCreate()

# #TODO(Done): Read about RDD Vs DF Vs Dataset
dfCar=spark.read.option("header",True).csv("/user/cars.csv").repartition(4)
dfCar.printSchema()
print(type(spark),type(dfCar))
dfCar.show(5)
print(dfCar.columns)
print(dfCar.rdd.getNumPartitions())
dfCar=dfCar.persist(storageLevel=StorageLevel.MEMORY_AND_DISK)
#========================================================================================================

"""# Task1: Extract a file which contains the car model and the country of origin of this car."""
#TODO(Done): Read about Transformation Vs Action: action create new RDD but transformation just update RDD
count=dfCar.count()
print("********************** Task1 start **********************")
dfCar.coalesce(1).write.mode("overwrite").csv('/user/dataParallel')

#========================================================================================================

"""# Task2: Extract one file per country"""
print("********************** Task2 start **********************")
dfCar.write.partitionBy('Country Of Origin').mode("overwrite").csv('/user/countryParallel')
print(dfCar.head(5))

#========================================================================================================

"""# Task3: Use caching properly to optimize the performance"""
print("********************** Task3 start **********************")
#TODO(Done): Use Cache Vs Persist: user choose the storagelevel , memory_only not serializable
#dfCar=dfCar.persist(storageLevel=StorageLevel.MEMORY_AND_DISK)

#========================================================================================================

"""# Task4: Expect to read a file with updated records, you should be able to merge these updates with the original dataset."""
print("********************** Task4 start **********************")

## Read 2015_State_Top10Report_wTotalThefts file
dfReport=spark.read.option("header",True).csv("/user/2015_State_Top10Report_wTotalThefts.csv").persist(storageLevel=StorageLevel.MEMORY_AND_DISK)
dfReport.count()
dfReport=dfReport.withColumn("Thefts", f.regexp_replace(dfReport.Thefts, ",", ""))
dfReport=dfReport.withColumn("Thefts",dfReport.Thefts.cast('long'))
dfReport.printSchema()
dfReport.show(50)
"""Rename some columns to make it easy to use them."""
dfReport=dfReport.withColumnRenamed('Make/Model','MakeModel').withColumnRenamed('Model Year','ModelYear')


"""## Read Updated - Sheet1 file"""
dfUpdate=spark.read.option("header",True).csv("/user/Updated_Sheet1.csv").persist(storageLevel=StorageLevel.MEMORY_AND_DISK)
dfUpdate.count()
dfUpdate=dfUpdate.na.drop("all")
dfUpdate=dfUpdate.withColumn("Thefts", f.regexp_replace(dfUpdate.Thefts, ",", ""))
dfUpdate=dfUpdate.withColumn("Thefts",dfUpdate.Thefts.cast('long'))
dfUpdate=dfUpdate.fillna(0, subset=['Thefts'])
dfUpdate.printSchema()
dfUpdate.show()
"""Rename some columns to make it easy to use them."""
dfUpdate=dfUpdate.withColumnRenamed('Make/Model','MakeModel').withColumnRenamed('Model Year','ModelYear')
print(dfUpdate.columns)



"""## Update the Report dataset using the updated dataset """
#TODO(Done): Explanation Inner and Outer: Inner just join data which matched by something, Outer join data even if it have not something matched
#TODO(Done): Update should be as => New record should be inserted and
#                             Update should be updated and
#                             Old record should be kept
dfUpdatedThefts = dfReport.join(dfUpdate.alias('b'), ['State', 'MakeModel', 'ModelYear', 'Rank'], how='outer')\
    .select('State','MakeModel','ModelYear','Rank', f.coalesce(dfUpdate.Thefts, dfReport.Thefts).alias('Thefts')).orderBy('State')

dfUpdatedThefts=dfUpdatedThefts.withColumn("Thefts",dfUpdatedThefts.Thefts.cast('long'))
dfUpdatedThefts.show()
dfUpdatedThefts.count()


dfUpdatedThefts=dfUpdatedThefts.withColumn("Thefts",dfUpdatedThefts.Thefts.cast('long'))
dfUpdatedThefts.persist(storageLevel=StorageLevel.MEMORY_AND_DISK)
"""# Create Cars table """
dfUpdatedThefts.createOrReplaceTempView("Cars")


#========================================================================================================

"""# Task5:List the most 5 thefted models in U.S"""
print("********************** Task5 start **********************")
#TODO(Done): Use Sum of the thefts insted of max thefts
spark.sql("select MakeModel,SUM(Thefts) from Cars GROUP BY MakeModel ORDER BY SUM(Thefts) desc LIMIT 5").show()

#========================================================================================================

"""# Task6:List the most 5 states based on the number of thefted cars."""
print("********************** Task6 start **********************")
#TODO(Done): Use Sum of the thefts insted of max thefts
spark.sql("select State,SUM(Thefts) from Cars GROUP BY State ORDER BY SUM(Thefts) desc LIMIT 5").show()

#========================================================================================================

"""# Task7:Based on the models, what is the most country from where Americans buy their cars
## Extract Model name
We need to extract model name then join it with it's country (using cars.csv file)"""
print("********************** Task7 start **********************")
#split_col = pyspark.sql.functions.split(dfUpdatedThefts['MakeModel'], ' ')
#dfUpdatedThefts = dfUpdatedThefts.withColumn('MakeModel', split_col.getItem(0))
dfUpdatedThefts.show(5)
numOfModelsBefore=dfUpdatedThefts.select('MakeModel').distinct().count()

"""Rename Car Brand column """
dfCar=dfCar.withColumnRenamed('Car Brand','CarBrand').withColumnRenamed('Country of Origin','CountryOfOrigin')
dfCar.show(5)

"""## Join cars dataset with report dataset"""
#dfUpdatedThefts=dfUpdatedThefts.join(dfCar, ['MakeModel'], 'inner')
dfUpdatedThefts = dfUpdatedThefts.join(dfCar, dfUpdatedThefts.MakeModel.contains(dfCar.CarBrand), how='inner')
dfUpdatedThefts.show(100)
numOfModelsAfter=dfUpdatedThefts.select('MakeModel').distinct().count()


"""**Important**"""
print("Number of models in cars.csv file = ",dfCar.select('CarBrand').distinct().count())
print("Number Of Models Before join  = ",numOfModelsBefore," Number Of Models After join  = ",numOfModelsAfter)
"""**Note:** VW, GMC, Seat, Pontiac, Acura weren't in cars.csv so the models number matched in report csv file and cars csv file is just 10 not 15.

## Calculate the most country repeted in cars report based on the model"""
dfUpdatedThefts.createOrReplaceTempView("Cars")
spark.sql("select CountryOfOrigin,count(*) as Number_Of_Buyers from Cars GROUP BY CountryOfOrigin ORDER BY count(*) desc LIMIT 1").show()
print("Done .. ")




