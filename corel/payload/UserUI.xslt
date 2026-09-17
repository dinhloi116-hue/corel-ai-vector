<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:frmwrk="Corel Framework Data" exclude-result-prefixes="frmwrk">
  <xsl:output method="xml" encoding="UTF-8" indent="yes"/>
  <frmwrk:uiconfig>
    <frmwrk:applicationInfo userConfiguration="true" />
    <frmwrk:compositeNode xPath="/uiConfig/dialogs/dialog[@guid='7FAF4D04-1B42-4C50-AEC4-4B2A59A4A801']"/>
    <frmwrk:compositeNode xPath="/uiConfig/views/viewTemplate[@guid='ab303a90-464d-5191-423f-613c4d1dcb2c']"/>
    <frmwrk:compositeNode xPath="/uiConfig/frame"/>
  </frmwrk:uiconfig>
  <xsl:template match="node()|@*"><xsl:copy><xsl:apply-templates select="node()|@*"/></xsl:copy></xsl:template>
  <xsl:template match="uiConfig/dialogs">
    <xsl:copy><xsl:apply-templates select="node()|@*"/>
      <xsl:if test="not(./dialog[@guidRef='7FAF4D04-1B42-4C50-AEC4-4B2A59A4A801'])">
        <dialog guidRef="7FAF4D04-1B42-4C50-AEC4-4B2A59A4A801" dock="top"/>
      </xsl:if>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>
