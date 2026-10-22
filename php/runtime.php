<?php
/** Compatibility support for trusted legacy application code, not user input. */
require_once __DIR__.'/vb425_php8_transformer.php';
foreach (['MYSQL_ASSOC'=>1,'MYSQL_NUM'=>2,'MYSQL_BOTH'=>3] as $vb425Name=>$vb425Value) {
    if (!defined($vb425Name)) define($vb425Name,$vb425Value);
}
unset($vb425Name,$vb425Value);
if (function_exists('mysqli_report')) mysqli_report(MYSQLI_REPORT_OFF);

function vb425_php8_each(&$value)
{
    if (!is_array($value)) throw new TypeError('Legacy each() requires an array');
    $key=key($value);
    if ($key===null) return false;
    $item=current($value); next($value);
    return [1=>$item,'value'=>$item,0=>$key,'key'=>$key];
}
function vb425_php8_count($value, int $mode=COUNT_NORMAL): int
{
    if (is_array($value) || $value instanceof Countable) return count($value,$mode);
    return $value===null?0:1;
}
function vb425_php8_implode($first, $second=null): string
{
    if (is_array($first)) return implode($second===null?'':(string)$second,$first);
    return implode((string)$first,$second);
}
function vb425_php8_magic_quotes(): bool { return false; }
function vb425_php8_number($value)
{
    return is_numeric((string)$value)?((string)$value+0):floatval($value);
}
function vb425_php8_closure($parameters,$body): Closure
{
    // vBulletin already evaluates administrator-authored templates/callbacks.
    // Do not call this function with untrusted request data.
    return eval(vb425_php8_fragment('return function('.$parameters.'){'.$body.'};'));
}
