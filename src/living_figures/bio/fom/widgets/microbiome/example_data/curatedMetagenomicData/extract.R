library(curatedMetagenomicData)
library(curatedMetagenomicAnalyses)
library(dplyr)

for(condition in c('cirrhosis', 'IBD', 'T1D', 'STEC', 'CRC')){
    se <- curatedMetagenomicAnalyses::makeSEforCondition(condition, dataType = "relative_abundance")
    df = data.frame(colData(se))
    write.csv(assay(se), paste0("CMD_", condition, ".abund.csv"))
    write.csv(df, paste0("CMD_", condition, ".annot.csv"))
}
