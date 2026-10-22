<?php
/** Original compatibility transformations; no vendor application is bundled. */
function vb425_php8_source(string $source): string
{
    $tokens = token_get_all($source);
    $calls = ['each'=>'vb425_php8_each', 'create_function'=>'vb425_php8_closure',
        'count'=>'vb425_php8_count', 'sizeof'=>'vb425_php8_count', 'implode'=>'vb425_php8_implode',
        'get_magic_quotes_gpc'=>'vb425_php8_magic_quotes', 'get_magic_quotes_runtime'=>'vb425_php8_magic_quotes'];
    $significant = [];
    foreach ($tokens as $i=>$t) {
        if (!is_array($t) || !in_array($t[0], [T_WHITESPACE,T_COMMENT,T_DOC_COMMENT], true)) $significant[]=$i;
    }
    $positions = array_flip($significant);
    $stack=[]; $quoted=false; $heredoc=false; $interpolation=0; $out=''; $offsetEnds=[];
    foreach ($tokens as $i=>$token) {
        $id=is_array($token)?$token[0]:null;
        $text=is_array($token)?$token[1]:$token;
        $p=$positions[$i]??null;
        $prev=$p!==null && $p>0?$tokens[$significant[$p-1]]:null;
        $next=$p!==null && isset($significant[$p+1])?$tokens[$significant[$p+1]]:null;
        $prevId=is_array($prev)?$prev[0]:$prev;
        $prevText=is_array($prev)?$prev[1]:$prev;
        if ($id===T_START_HEREDOC) $heredoc=true;
        if ($id===T_END_HEREDOC) $heredoc=false;
        if ($token==='"' || $token==='`') $quoted=!$quoted;
        $code=!$quoted && !$heredoc || $interpolation>0;
        if ($id===T_STRING && $code) {
            $name=strtolower($text);
            $beforePrev=$p!==null && $p>=2?$tokens[$significant[$p-2]]:null;
            $beforePrevId=is_array($beforePrev)?$beforePrev[0]:$beforePrev;
            $declaration=$beforePrevId===T_FUNCTION && in_array($prevText,['&'],true);
            if (isset($calls[$name]) && $next==='(' && !$declaration && !in_array($prevId,[T_OBJECT_OPERATOR,T_NULLSAFE_OBJECT_OPERATOR,T_DOUBLE_COLON,T_FUNCTION,T_NEW],true)) {
                $text=$calls[$name];
            } elseif ($text==='SAPI_NAME' && !in_array($prevId,[T_OBJECT_OPERATOR,T_DOUBLE_COLON,T_FUNCTION],true)) {
                $text='PHP_SAPI';
            } elseif ($text==='E_STRICT' && !in_array($prevId,[T_OBJECT_OPERATOR,T_DOUBLE_COLON],true)) {
                $text='2048';
            } elseif ($prev==='[' && $next===']' && preg_match('/^[a-z_][a-z0-9_]*$/D',$text)
                && !in_array($name,['true','false','null'],true) && !defined($text)) {
                $text="'".$text."'";
            } elseif ($prev==='(' && $p>=2 && is_array($tokens[$significant[$p-2]])
                && strtolower($tokens[$significant[$p-2]][1])==='defined' && $next===')') {
                $text="'".$text."'";
            }
        }
        if ($id===T_NAME_FULLY_QUALIFIED && $code && isset($calls[strtolower(substr($text,1))]) && $next==='(') {
            $text='\\'.$calls[strtolower(substr($text,1))];
        }
        if ($id===T_DOUBLE_CAST && preg_match('/real/i',$text)) $text='(float)';
        if ($id===T_CURLY_OPEN || $id===T_DOLLAR_OPEN_CURLY_BRACES) {
            $stack[]='interpolation'; $interpolation++;
        } elseif ($token==='{') {
            $property=$prevId===T_STRING && $p>=2 && in_array(is_array($tokens[$significant[$p-2]])?$tokens[$significant[$p-2]][0]:null,[T_OBJECT_OPERATOR,T_NULLSAFE_OBJECT_OPERATOR],true);
            $offset=$code && ($prevId===T_VARIABLE || $prev===']' || $property || $p>0 && isset($offsetEnds[$significant[$p-1]]));
            $stack[]=$offset?'offset':'block';
            if ($offset) $text='[';
        } elseif ($token==='}' && $stack) {
            $kind=array_pop($stack);
            if ($kind==='interpolation') $interpolation--;
            if ($kind==='offset') { $text=']'; $offsetEnds[$i]=true; }
        }
        $out.=$text;
    }
    return $out;
}

function vb425_php8_fragment(string $source): string
{
    static $cache=[];
    $key=hash('sha256',$source);
    if (isset($cache[$key])) return $cache[$key];
    if (count($cache)>512) $cache=[];
    return $cache[$key]=substr(vb425_php8_source("<?php\n".$source),6);
}
