// TmdlCheck: load a TMDL semantic model with TOM (no engine, no Windows), validate it,
// and check it against a set of Best Practice Analyzer style rules.
//
//   dotnet run --project tools/TmdlCheck -- models/<name>/<Name>.SemanticModel/definition
//
// Exit code 0 = loads, validates and passes every rule marked "error"; 1 = otherwise.

using System.Text.RegularExpressions;
using Microsoft.AnalysisServices.Tabular;
using Microsoft.AnalysisServices.Tabular.Tmdl;

if (args.Length < 1)
{
    Console.Error.WriteLine("usage: TmdlCheck <path to .SemanticModel/definition folder>");
    return 2;
}

var folder = Path.GetFullPath(args[0]);
Database db;
try
{
    db = TmdlSerializer.DeserializeDatabaseFromFolder(folder);
}
catch (TmdlFormatException e)
{
    Console.WriteLine($"FAIL  TMDL syntax: {e.Message}");
    if (e.HasDocumentSourceInfo) Console.WriteLine($"      {e.Document}:{e.Line}  {e.LineText}");
    return 1;
}
catch (TmdlSerializationException e)
{
    Console.WriteLine($"FAIL  TMDL semantics: {e.Message}");
    if (e.HasDocumentSourceInfo) Console.WriteLine($"      {e.Document}:{e.Line}");
    return 1;
}

var m = db.Model;
Console.WriteLine($"OK    TOM loaded '{db.Name}' (compatibility {db.CompatibilityLevel}): " +
    $"{m.Tables.Count} tables, {m.Tables.Sum(t => t.Columns.Count(c => c.Type != ColumnType.RowNumber))} columns, " +
    $"{m.Tables.Sum(t => t.Measures.Count)} measures, {m.Relationships.Count} relationships, {m.Expressions.Count} expressions");

var validation = m.Validate();
if (validation.ContainsErrors)
{
    foreach (var err in validation.Errors) Console.WriteLine($"FAIL  TOM validation: {err.Message}");
    return 1;
}
Console.WriteLine("OK    TOM Model.Validate(): no errors");

// Round trip: serialize back to TMDL in memory to prove the object graph is complete.
var tmp = Path.Combine(Path.GetTempPath(), "tmdlcheck-" + Guid.NewGuid().ToString("N"));
TmdlSerializer.SerializeDatabaseToFolder(db, tmp);
TmdlSerializer.DeserializeDatabaseFromFolder(tmp);
Directory.Delete(tmp, true);
Console.WriteLine("OK    Round trip TMDL -> TOM -> TMDL -> TOM");
Console.WriteLine();

// ---- Best-practice rules ------------------------------------------------------------
var columns = m.Tables.SelectMany(t => t.Columns).Where(c => c.Type != ColumnType.RowNumber).ToList();
var measures = m.Tables.SelectMany(t => t.Measures).ToList();
var rels = m.Relationships.OfType<SingleColumnRelationship>().ToList();
var fkColumns = rels.Select(r => r.FromColumn).ToHashSet();
var pkColumns = rels.Select(r => r.ToColumn).ToHashSet();
var numeric = new[] { DataType.Int64, DataType.Double, DataType.Decimal };
string N(Column c) => $"'{c.Table.Name}'[{c.Name}]";
string NM(Measure x) => $"[{x.Name}]";

var rules = new List<(string id, string category, string name, bool error, IEnumerable<string> violations)>
{
    ("DOC1", "Maintenance", "Every table has a description", true,
        m.Tables.Where(t => string.IsNullOrWhiteSpace(t.Description)).Select(t => t.Name)),
    ("DOC2", "Maintenance", "Every column has a description", true,
        columns.Where(c => string.IsNullOrWhiteSpace(c.Description)).Select(N)),
    ("DOC3", "Maintenance", "Every measure has a description", true,
        measures.Where(x => string.IsNullOrWhiteSpace(x.Description)).Select(NM)),
    ("DOC4", "Maintenance", "Every expression (parameter, shared query) has a description", true,
        m.Expressions.Where(e => string.IsNullOrWhiteSpace(e.Description)).Select(e => e.Name)),
    ("FMT1", "Formatting", "Provide a format string for measures", true,
        measures.Where(x => string.IsNullOrWhiteSpace(x.FormatString) && x.FormatStringDefinition == null).Select(NM)),
    ("FMT2", "Formatting", "Visible measures are organised in display folders", true,
        measures.Where(x => !x.IsHidden && string.IsNullOrWhiteSpace(x.DisplayFolder)).Select(NM)),
    ("FMT3", "Formatting", "Do not summarize numeric columns (summarizeBy none)", true,
        columns.Where(c => numeric.Contains(c.DataType) && c.SummarizeBy != AggregateFunction.None).Select(N)),
    ("FMT4", "Formatting", "Discourage implicit measures at model level", true,
        m.DiscourageImplicitMeasures ? [] : ["model"]),
    ("FMT5", "Formatting", "Hide foreign keys", true,
        fkColumns.Where(c => !c.IsHidden).Select(N)),
    ("FMT6", "Formatting", "Mark primary keys (isKey) on dimension keys", true,
        pkColumns.Where(c => !c.IsKey).Select(N)),
    ("FMT7", "Formatting", "Month and weekday name columns have a sort-by column", true,
        columns.Where(c => Regex.IsMatch(c.Name, @"Month( Name| Short)?$|Day of Week$|Year Month$|Year Quarter$|Day Part$")
                           && c.DataType == DataType.String && c.SortByColumn == null).Select(N)),
    ("FMT8", "Formatting", "Percentage measures use a percent format", true,
        measures.Where(x => Regex.IsMatch(x.Name, @"%|Rate") && !(x.FormatString ?? "").Contains('%')).Select(NM)),
    ("FMT9", "Formatting", "Object names have no leading/trailing spaces and start with a capital", true,
        m.Tables.Select(t => t.Name).Concat(columns.Select(c => c.Name)).Concat(measures.Select(x => x.Name))
          .Where(n => n != n.Trim() || (char.IsLetter(n[0]) && !char.IsUpper(n[0])))),
    ("MOD1", "Model layout", "The model has a date table marked as a date table", true,
        m.Tables.Any(t => t.DataCategory == "Time" && t.Columns.Any(c => c.IsKey && c.DataType == DataType.DateTime)) ? [] : ["no marked date table"]),
    ("MOD2", "Model layout", "Auto date/time is off", true,
        m.Annotations.Find("__PBI_TimeIntelligenceEnabled")?.Value == "0" ? [] : ["__PBI_TimeIntelligenceEnabled is not 0"]),
    ("MOD3", "Model layout", "No bi-directional relationships", true,
        rels.Where(r => r.CrossFilteringBehavior == CrossFilteringBehavior.BothDirections).Select(r => r.Name)),
    ("MOD4", "Model layout", "No many-to-many relationships", true,
        rels.Where(r => r.FromCardinality == RelationshipEndCardinality.Many && r.ToCardinality == RelationshipEndCardinality.Many).Select(r => r.Name)),
    ("MOD5", "Model layout", "Relationships go many (fact) to one (dimension)", true,
        rels.Where(r => !(r.FromCardinality == RelationshipEndCardinality.Many && r.ToCardinality == RelationshipEndCardinality.One)).Select(r => r.Name)),
    ("MOD6", "Model layout", "Relationship columns on both ends share a data type", true,
        rels.Where(r => r.FromColumn.DataType != r.ToColumn.DataType).Select(r => r.Name)),
    ("MOD7", "Model layout", "Every table is related (no islands) except parameter/measure tables", true,
        m.Tables.Where(t => !rels.Any(r => r.FromTable == t || r.ToTable == t)).Select(t => t.Name)),
    ("MOD8", "Model layout", "Every table has a description-bearing partition with an M source", true,
        m.Tables.Where(t => t.Columns.Any(c => c.Type == ColumnType.Data) && !t.Partitions.Any(p => p.Source is MPartitionSource || p.Source is PolicyRangePartitionSource))
          .Select(t => t.Name)),
    ("PRF1", "Performance", "Do not use floating point data types (use fixed decimal)", true,
        columns.Where(c => c.DataType == DataType.Double).Select(N)),
    ("PRF2", "Performance", "Fact table columns are hidden (exposed through measures)", true,
        m.Tables.Where(t => rels.Any(r => r.FromTable == t)).SelectMany(t => t.Columns)
          .Where(c => c.Type != ColumnType.RowNumber && !c.IsHidden).Select(N)),
    ("PRF3", "Performance", "Large fact tables use an incremental refresh policy", false,
        m.Tables.Where(t => rels.Any(r => r.FromTable == t) && t.RefreshPolicy == null).Select(t => t.Name)),
    ("PRF4", "Performance", "Set IsAvailableInMDX false on hidden fact columns", false,
        m.Tables.Where(t => rels.Any(r => r.FromTable == t)).SelectMany(t => t.Columns)
          .Where(c => c.Type == ColumnType.Data && c.IsHidden && c.IsAvailableInMDX && !fkColumns.Contains(c)).Select(N)),
    ("DAX1", "DAX expressions", "Use DIVIDE() instead of the / operator", true,
        measures.Where(x => Regex.IsMatch(StripStrings(x.Expression), @"[\]\)\w]\s*/\s*[\[\(\w']")).Select(NM)),
    ("DAX2", "DAX expressions", "Avoid IFERROR and ISERROR", true,
        measures.Where(x => Regex.IsMatch(x.Expression, @"\b(IFERROR|ISERROR)\s*\(", RegexOptions.IgnoreCase)).Select(NM)),
    ("DAX3", "DAX expressions", "Fully qualify column references, never qualify measure references", true,
        measures.SelectMany(x => DaxRefIssues(x, m)).ToList()),
    ("DAX4", "DAX expressions", "Measure names are unique and do not collide with column names", true,
        measures.Where(x => columns.Any(c => c.Name.Equals(x.Name, StringComparison.OrdinalIgnoreCase))).Select(NM)
          .Concat(measures.GroupBy(x => x.Name, StringComparer.OrdinalIgnoreCase).Where(g => g.Count() > 1).Select(g => g.Key))),
    ("DAX5", "DAX expressions", "Measures reference only objects that exist", true,
        measures.SelectMany(x => MissingRefs(x, m)).ToList()),
};

int errors = 0;
foreach (var (id, category, name, error, violations) in rules)
{
    var v = violations.ToList();
    var status = v.Count == 0 ? "PASS" : error ? "FAIL" : "WARN";
    if (v.Count > 0 && error) errors++;
    Console.WriteLine($"{status}  {id,-5} {category,-16} {name}");
    foreach (var item in v.Take(12)) Console.WriteLine($"            - {item}");
    if (v.Count > 12) Console.WriteLine($"            ... and {v.Count - 12} more");
}
Console.WriteLine();
Console.WriteLine(errors == 0 ? "All error-level rules pass." : $"{errors} rule(s) failed.");
return errors == 0 ? 0 : 1;

static string StripStrings(string dax) =>
    Regex.Replace(Regex.Replace(Regex.Replace(dax, "\"[^\"]*\"", "\"\""), @"--[^\n]*|//[^\n]*", ""), @"\[[^\]]*\]", "[x]");

static IEnumerable<string> DaxRefIssues(Measure x, Model m)
{
    var dax = Regex.Replace(x.Expression, "\"[^\"]*\"", "\"\"");
    // Table-qualified references: 'Table'[Name] or Table[Name]
    foreach (Match r in Regex.Matches(dax, @"('(?<t>[^']+)'|(?<t>\b[A-Za-z_][\w]*))\[(?<n>[^\]]+)\]"))
    {
        var t = m.Tables.Find(r.Groups["t"].Value);
        if (t != null && t.Measures.Contains(r.Groups["n"].Value))
            yield return $"[{x.Name}] qualifies measure {r.Value}";
    }
    // Unqualified references: [Name] not preceded by a table name
    foreach (Match r in Regex.Matches(dax, @"(?<!['\w])\[(?<n>[^\]]+)\]"))
    {
        var n = r.Groups["n"].Value;
        if (!m.Tables.Any(t => t.Measures.Contains(n)) && m.Tables.Any(t => t.Columns.Contains(n)))
            yield return $"[{x.Name}] has unqualified column [{n}]";
    }
}

static IEnumerable<string> MissingRefs(Measure x, Model m)
{
    var dax = Regex.Replace(x.Expression, "\"[^\"]*\"", "\"\"");
    foreach (Match r in Regex.Matches(dax, @"('(?<t>[^']+)'|(?<t>\b[A-Za-z_][\w]*))\[(?<n>[^\]]+)\]"))
    {
        var t = m.Tables.Find(r.Groups["t"].Value);
        if (t == null) { yield return $"[{x.Name}] -> unknown table {r.Groups["t"].Value}"; continue; }
        if (!t.Columns.Contains(r.Groups["n"].Value) && !t.Measures.Contains(r.Groups["n"].Value))
            yield return $"[{x.Name}] -> unknown column {r.Value}";
    }
    foreach (Match r in Regex.Matches(dax, @"(?<!['\w])\[(?<n>[^\]]+)\]"))
    {
        var n = r.Groups["n"].Value;
        if (!m.Tables.Any(t => t.Measures.Contains(n) || t.Columns.Contains(n)))
            yield return $"[{x.Name}] -> unknown measure [{n}]";
    }
}
