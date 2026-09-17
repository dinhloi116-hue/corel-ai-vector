<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:frmwrk="Corel Framework Data">
  <xsl:output method="xml" encoding="UTF-8" indent="yes"/>
  <frmwrk:uiconfig><frmwrk:applicationInfo userConfiguration="true" /></frmwrk:uiconfig>
  <xsl:template match="node()|@*"><xsl:copy><xsl:apply-templates select="node()|@*"/></xsl:copy></xsl:template>
  <xsl:template match="uiConfig/items">
    <xsl:copy><xsl:apply-templates select="node()|@*"/>
      <itemData guid="94D0B409-C5A6-4477-A3D9-63B6E49C4F31" type="browser" suppressDialogs="true"
                href="[VGAppAddonsDir]/CorelAIVector/CorelAIVector.html" enable="true" />
    </xsl:copy>
  </xsl:template>
  <xsl:template match="uiConfig/dialogs">
    <xsl:copy><xsl:apply-templates select="node()|@*"/>
      <dialog guid="7FAF4D04-1B42-4C50-AEC4-4B2A59A4A801" sheetMode="false" width="470" height="820" resizable="true" caption="Corel AI Vector">
        <container><item guidRef="94D0B409-C5A6-4477-A3D9-63B6E49C4F31" dock="fill" /></container>
      </dialog>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>
